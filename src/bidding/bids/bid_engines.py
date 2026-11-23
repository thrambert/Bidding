"""
This module manages the bidding phase for the distributed deal.
It starts with the dealer, then it passes to the next player in a
clockwise direction, and stops after 3 passes.
"""

import logging
import operator
import re

from bridgebots.deal import PlayerHand
from bridgebots.deal_enums import Rank

from bidding.bids.bid_producers import BidProducer
from bidding.bids.bid_records import BidRecord
from bidding.bids.bid_rules import BidRule
from bidding.bids.bid_senses import BidSense
from bidding.bids.bids import Bid, SuitsToStop
from bidding.bids.hands import MetaSuit, RichHand
from bidding.bids.hazes import Haze
from bidding.bids.points import PointZone
from bidding.bids.slams import Slam
from bidding.bids.steps import Stair
from bidding.bids.takeout_double import TakeoutDouble
from bidding.utils import MyDataException

logger = logging.getLogger(__name__)


_OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "=": operator.eq,
    "==": operator.eq,
    None: operator.eq,
}
_INEQUALITY_RE = re.compile(r"\s*(<=|>=|==|<|>|=)?\s*(\d+(?:[.,]\d+)?)\s*")


class BidEngine:
    """
    This class is an engine to determine which bid a player should make.
    It remains active while players are bidding, and it stores each bid made
    into record property.
    It uses rules coming from Excel sheet, and it delegates the rules analyzis
    to class RuleAnalyzer.

    Properties
    hand:          The current player's hand, for who a bid should be decided.
    relative_vuln: Player relative vulnerability: 0 neutral, 1 favorable, -1 unf.
    player_rank:   Rank of current player who has to make a bid.
    record:        All bids made since the game starts.
    haze:          Information on each player's hand deducted from bidding.
    producer:      Bid producer when there are no rules, which stores slam sequence.
    """

    def __init__(self):
        self.hand: RichHand = None
        self.relative_vuln = 0
        self.player_rank = 1
        self.record = BidRecord()
        self.haze = Haze()
        self.producer: BidProducer = None
        self._opp_next_step = ""
        self.stair = Stair()

    def provide_bid(self, hand: PlayerHand, relative_vuln: int) -> BidSense:
        """
        This function returns bid the player has to make as a BidSense instance
        in which properties may be empty except bid if no sense to provide.
        """
        self.hand = RichHand(hand)
        self.relative_vuln = relative_vuln
        player_lap, self.player_rank = self.record.next_lap_and_rank(False)
        step = self._get_next_step(10 * player_lap + self.player_rank)
        sense = self._get_next_bid(step)

        if not sense:
            logger.warning("No bid sense found at step %s", step)

        self.record.add_bidding(sense)
        self._store_in_haze(sense)
        return sense

    def _store_in_haze(self, sense: BidSense):
        to_stop = {}
        opp_camp = self.record.last.camp.other_camp()
        unnamed = set(MetaSuit.four_suit_codes()) - self.record.suit_codes()
        to_stop[SuitsToStop.OPP] = self.record.suit_codes(opp_camp)
        to_stop[SuitsToStop.UNNAMED] = self.record.suit_codes(opp_camp) | unnamed
        self.haze.store(sense, self.player_rank, self.record.third_last, to_stop)

    def _get_next_bid(self, step: str) -> BidSense:
        if step == "FREE":
            if self.producer is None:
                self.producer = BidProducer(self.haze)
            return self.producer.make_bid(self.hand, self.record)
        else:
            return self._run_step(step)

    def _get_next_step(self, lap_rank: int) -> str:
        if self.record.last:
            return self.stair.get_next(self.record.no_bid_wo_pass(), lap_rank, self.record.sleep())
        else:
            return self.stair.get_next(True, 1, False)

    def _set_next_steps(self, rule: BidRule):
        next_opp_rank = BidRecord.next_rank(self.player_rank)
        partner_rank = BidRecord.next_rank(next_opp_rank)
        self.stair.set_next_step(partner_rank, rule.camp_next_step if rule else "")
        if rule and rule.opp_next_step:
            self.stair.set_next_step(next_opp_rank, rule.opp_next_step)

    def _run_step(self, step_name: str) -> BidSense:
        rule = self._get_first_satisfied_rule(step_name)
        self._set_next_steps(rule)
        if rule:
            return self._get_bid_sense(rule)
        else:
            return BidSense.passe()

    def _get_bid_sense(self, rule: BidRule) -> BidSense:
        if rule.sense_id:
            sense = BidSense.get(rule.sense_id)
            if sense is None:
                raise MyDataException(f"Règle {rule.id} : sense_id {rule.sense_id} introuvable")
            sense.raw_bid = rule.raw_bid
        else:
            sense = BidSense(id=0, raw_bid=rule.raw_bid)
        sense._rule_id = rule.id
        return sense

    def _get_first_satisfied_rule(self, step_name: str) -> BidRule | None:
        """
        Returns a copy of first satisfied rule in which raw_bid is computed with
        function_bid if required. If no rule satisfies, returns None.
        """
        analyzer = RuleAnalyzer(self.hand, self.relative_vuln, self.record, self.haze)
        for rule in BidRule.get_rules(step_name):
            if raw_bid := analyzer.satisfied_bid(rule):
                return rule.model_copy(update={"raw_bid": raw_bid})
        return None


class RuleAnalyzer:
    """
    ════════════════════════════════════════════════════════════════════════════
    This class examines rules for a given hand at a given stage of bidding.

    The unique public method checks all conditions contained in a rule to see if
    the rule is satisfied. It launches functions whose names are deducted from
    header of Excel rules columns, and true if all conditions of a rule are
    satisfied. Conditions are Excel cells in row of given rule.

    Properties
    hand:          The current player's hand, for who a bid should be decided.
    relative_vuln: Player relative vulnerability: 0 neutral, 1 favorable, -1: unf.
    record:        All bids made since the game starts.
    haze:          Information on each player's hand deducted from bidding.
    ════════════════════════════════════════════════════════════════════════════
    """

    def __init__(self, hand: RichHand, relative_vuln: int, record: BidRecord, haze: Haze):
        self.hand = hand
        self.relative_vuln = relative_vuln
        self.record = record
        self.haze = haze

    def satisfied_bid(self, rule: BidRule) -> str | None:
        """
        Returns the raw bid to make if all conditions of rule are satisfied and
        if the bid (given by raw_bid, or computed with function_bid) is higher
        than last bid made. Otherwise returns None. Rule is not modified.
        """
        for condition_name in BidRule.condition_names():
            # Empty attributes in rule are not conditions.
            if getattr(rule, condition_name):
                if not getattr(self, f"_{condition_name}_check")(rule):
                    return None

        raw_bid = rule.raw_bid or self._compute_bid(rule.function_bid, rule.arg_bid)
        bid = Bid(raw_bid)
        if self.record.no_open() or bid.a_special or self.record.last_normal_bid() < bid:
            return raw_bid
        return None

    def _compute_bid(self, function_bid: str, arg: str) -> str:
        bid_computer = BidComputer(self.hand, self.record, self.haze)
        raw_bid = bid_computer.run(function_bid, arg)
        return raw_bid

    def op_match(self, math_inequality: str, value: float) -> bool:
        """
        Returns True if value satisfies math inequality, which is one of
        <n, <=n, >n, >=n, =n, ==n or n (meaning equal). n may be decimal,
        with "." or "," as separator.
        """
        match = _INEQUALITY_RE.fullmatch(math_inequality)
        if not match:
            raise MyDataException(f"Condition invalide : {math_inequality!r}")
        op, number = match.groups()
        return _OPERATORS[op](value, float(number.replace(",", ".")))

    #  ═════════════════════════════════════════════════════════════════════════
    #  Basic conditions
    #  ═════════════════════════════════════════════════════════════════════════

    def _points_check(self, rule: BidRule) -> bool:
        point_zone = PointZone(rule.points)
        if point_zone.is_HLD():
            return point_zone.contains_HLD(self._get_player_HLD())
        else:
            return point_zone.contains(self.hand.points_H, self.hand.points_HL)

    def _get_player_HLD(self) -> int:
        fit = self.haze.fit(self.hand.cards_count, self.record.second_last.rank)
        if fit:
            return self.hand.points_HLD(fit.suit, fit.partner_count)
        else:
            return self.hand.points_HL

    def _distribution_check(self, rule: BidRule) -> bool:
        return rule.distribution in self.hand.distribution

    def _bicolor_check(self, rule: BidRule) -> bool:
        rule_suit_text = rule.bicolor.split(",")
        requested_suits = [MetaSuit.from_text(t) for t in rule_suit_text]
        return all(s in self.hand.longest_suits for s in requested_suits)

    def _suit1_check(self, rule: BidRule) -> bool:
        player_longest_suit = self.hand.longest_suits[0]
        return rule.suit1 in player_longest_suit.any_texts()

    def _suit1_count_check(self, rule: BidRule) -> bool:
        return self.op_match(rule.suit1_count, self.hand.count_longest[0])

    def _suit2_check(self, rule: BidRule) -> bool:
        player_2nd_longest_suit = self.hand.longest_suits[1]
        return rule.suit2 in player_2nd_longest_suit.any_texts()

    def _suit2_count_check(self, rule: BidRule) -> bool:
        return self.op_match(rule.suit2_count, self.hand.count_longest[1])

    def _first_pass_check(self, rule: BidRule) -> bool:
        return self.op_match(rule.first_pass, self.record.first_pass_count())

    def _won_tricks_check(self, rule: BidRule) -> bool:
        return self.hand.won_tricks >= rule.won_tricks

    def _def_tricks_check(self, rule: BidRule) -> bool:
        return self.op_match(rule.def_tricks, self.hand.def_tricks)

    def _lost_tricks_check(self, rule: BidRule) -> bool:
        lost_tricks = int(rule.lost_tricks[0])
        adjustment = self.relative_vuln if rule.lost_tricks[-1] == "V" else 0
        return self.hand.lost_tricks <= lost_tricks + adjustment

    def _fit_cards_check(self, rule: BidRule) -> bool:
        if self.record.second_last:
            partner_suit = self.record.second_last.suit
            if partner_suit and partner_suit != MetaSuit.NO_TRUMP:
                player_cards_count = self.hand.cards_count[partner_suit]
                return self.op_match(rule.fit_cards, player_cards_count)
        return False

    def _stops_check(self, rule: BidRule) -> bool:
        opp_camp = self.record.last.camp
        opp_last_suit_code = self.record.last_suit_code(opp_camp)
        if opp_last_suit_code:
            suit = MetaSuit.from_code(opp_last_suit_code)
            return self.hand.stops_count(suit) >= rule.stops
        else:
            return True

    def _awake_check(self, rule: BidRule) -> bool:
        if rule.awake:
            return self.record.last_pass_count() == 2
        else:
            return True

    def _hist_bid_check(self, rule: BidRule) -> bool:
        requested_raw_bids = list(reversed(rule.polished_hist_bid().split(" ")))
        requested_bids = [Bid(value) for value in requested_raw_bids]
        return self.record.comply_with(requested_bids, rule.hist_bid_is_partial())

    #  ═════════════════════════════════════════════════════════════════════════
    #  Conditions as functions
    #  ═════════════════════════════════════════════════════════════════════════

    def _function1_check(self, rule: BidRule) -> bool:
        function_name = "_" + rule.function1 + "_check"
        condition_check = getattr(self, function_name)
        return condition_check()

    def _function2_check(self, rule: BidRule) -> bool:
        function_name = "_" + rule.function2 + "_check"
        condition_check = getattr(self, function_name)
        return condition_check(rule.arg2)

    def _no_good_major_5_check(self) -> bool:
        suit = self.hand.longest_suits[0]
        return not (
            suit.is_major()
            and self.hand.count_longest[0] == 5
            and self.hand.suit_points_H(suit) >= 6
        )

    def _major_3_check(self) -> bool:
        majors_3 = [n for n in self.hand.majors_count.values() if n == 3]
        return len(majors_3) >= 1

    def _major_4_check(self) -> bool:
        majors_4 = [n for n in self.hand.majors_count.values() if n == 4]
        return len(majors_4) >= 1

    def _any_short_color_check(self) -> bool:
        return min(self.hand.cards_count.values()) <= 1

    def _short_in_interv_color_check(self) -> bool:
        intervention_suit_code = self.record.last_suit_code(self.record.last.camp)
        intervention_suit = MetaSuit.from_code(intervention_suit_code)
        return self.hand.cards_count[intervention_suit] <= 1

    def _not_5_in_interv_color_check(self) -> bool:
        intervention_suit_code = self.record.last_suit_code(self.record.last.camp)
        intervention_suit = MetaSuit.from_code(intervention_suit_code)
        return self.hand.cards_count[intervention_suit] < 5

    def _honors_in_bicolors_check(self) -> bool:
        pts_H = [self.hand.suit_points_H(s) for s in self.hand.longest_suits]
        points_H_in_bicolors = sum(pts_H)
        return points_H_in_bicolors >= self.hand.points_H - 2

    def _honors_in_short_colors_check(self) -> bool:
        suits = [s for s, count in self.hand.cards_count.items() if count <= 2]
        for suit in suits:
            ok = self.hand.suit_points_H(suit) >= 4 or (self.hand.king_second(suit))
            if not ok:
                return False
        return True

    def _long_suit_1_unnamed_check(self) -> bool:
        suit_code = self.hand.longest_suits[0].code
        named_suits = [b.suit_code for b in self.record.all if b.a_color]
        return suit_code not in named_suits

    def _long_suit_2_unnamed_check(self) -> bool:
        suit_code = self.hand.longest_suits[1].code
        named_suits = [b.suit_code for b in self.record.all if b.a_color]
        return suit_code not in named_suits

    def _takeout_double_check(self) -> bool:
        """Returns True if distribution is ok for a takeout double (contre d'appel)"""
        opp_suit_codes = self.record.suit_codes(self.record.last.camp)
        takeout_double = TakeoutDouble(self.hand.cards_count, opp_suit_codes)
        return takeout_double.allowed()

    def _no_unnamed_major_4_check(self) -> bool:
        opp_suit_codes = self.record.suit_codes(self.record.last.camp)
        for suit, nbr in self.hand.cards_count.items():
            if suit.is_major() and nbr >= 4 and suit.code not in opp_suit_codes:
                return False
        return True

    def _stop_opponents_suits_check(self) -> bool:
        opp_camp = self.record.last.camp
        for suit_code in self.record.suit_codes(opp_camp):
            suit = MetaSuit.from_code(suit_code)
            if self.hand.stops_count(suit) < 1:
                return False
        return True

    def _stop_unnamed_suits_check(self) -> bool:
        player_camp = self.record.last.camp.other_camp()
        for suit_code in self.record.suit_codes(player_camp):
            suit = MetaSuit.from_code(suit_code)
            if self.hand.stops_count(suit) < 1:
                return False
        return self._stop_opponents_suits_check()

    def _has_strength_check(self) -> bool:
        camp_suits = self.record.suit_codes(self.record.second_last.camp)
        strengths = [s for s in self.hand.strong_suits if s.code not in camp_suits]
        return len(strengths) >= 1

    def _one_major_ace_check(self) -> bool:
        return self.hand.has_one_major_ace_and_no_minor()

    def _unnamed_3_cards_check(self, arg: str) -> bool:
        """Returns True if player has at least 3 cards in unnamed suits"""
        named = self.record.suit_codes()
        unnamed = [s for s in MetaSuit.four_suits() if s.code not in named]
        return all(self.hand.cards_count[s] >= 3 for s in unnamed)

    def _suit_length_check(self, arg: str) -> bool:
        meta_suit = MetaSuit.from_code(arg[0])
        suit_length = self.hand.cards_count[meta_suit]
        condition = arg[1:]
        return self.op_match(math_inequality=condition, value=suit_length)

    def _no_short_suit_check(self, arg: str) -> bool:
        """
        Returns True if every given suits have 2 cards at least
        Arg = "CD..." or "", where CD... are suit codes.
        If arg = "", all suits are concerned.
        """
        suit_codes = list(arg) if arg else ["T", "K", "C", "P"]
        suits_to_check = [MetaSuit.from_code(s) for s in suit_codes]
        for suit in suits_to_check:
            if self.hand.cards_count[suit] < 2:
                return False
        return True

    def _longest_major_check(self, arg: str) -> bool:
        longest_count = max(self.hand.majors_count.values())
        return self.op_match(math_inequality=arg, value=longest_count)

    def _majors_at_least_4_check(self, arg: str) -> bool:
        majors_at_least_4 = [n for n in self.hand.majors_count.values() if n >= 4]
        count = len(majors_at_least_4)
        return self.op_match(math_inequality=arg, value=count)

    def _long_color_points_H_check(self, arg: str) -> bool:
        """n'importe quoi !"""
        longest_suit = self.hand.longest_suits[0]
        longest_suit_pts_H = self.hand.suit_points_H(longest_suit)
        return self.op_match(math_inequality=arg, value=longest_suit_pts_H)

    def _long_over_previous_check(self, arg: str) -> bool:
        over = arg == "True"
        longest_suit = self.hand.longest_suits[0]
        previous_suit = MetaSuit.from_code(self.record.last_normal_bid().suit_code)
        return previous_suit < longest_suit if over else longest_suit < previous_suit

    def _stop_suit_check(self, arg: str) -> bool:
        raw_arg = arg.replace(" ", "")
        suit = MetaSuit.from_code(raw_arg[0])
        nbr_stops = float(raw_arg[1:].replace(",", "."))
        return self.hand.stops_count(suit) >= nbr_stops

    def _stop_suits_check(self, arg: str) -> bool:
        suits_codes_to_stop = arg.replace(" ", "").split(",")
        for suit in [MetaSuit.from_code(c) for c in suits_codes_to_stop]:
            if self.hand.stops_count(suit) < 1:
                return False
        return True

    def _points_H_check(self, arg: str) -> bool:
        """Condition on honor points in a suit, arg = "Cn" where C is a suit code."""
        suit = MetaSuit.from_code(arg[0])
        return self.op_match(math_inequality=arg[1:], value=self.hand.suit_points_H(suit))

    def _control_check(self, arg: str) -> bool:
        suit = MetaSuit.from_code(arg)
        return self.hand.controls(suit)

    def _cards_gap_check(self, arg: str) -> bool:
        """
        Returns true if nbr cards in suit C <= nbr D - n, with
        arg = "CDn" where C and D are suit codes and n >= 0
        """
        suit_codes = [arg[0], arg[1]]
        gap = int(arg[2])
        suits = [MetaSuit.from_code(c) for c in suit_codes]
        card_counts = [self.hand.cards_count[s] for s in suits]
        return card_counts[0] <= card_counts[1] - gap

    def _ace_check(self, arg: str) -> bool:
        suit = MetaSuit.from_code(arg[0])
        ranks = self.hand.suits[suit]
        return len(ranks) >= int(arg[1]) and ranks[:1] == [Rank.ACE]

    def _aces_count_check(self, arg: str) -> bool:
        math_expr = arg
        return self.op_match(math_inequality=math_expr, value=self.hand.aces_count())

    def _covering_count_check(self, arg: str) -> bool:
        suit_codes = list(arg[:2])
        math_expr = arg[2:]
        suits = [MetaSuit.from_code(c) for c in suit_codes]
        covering_count = self.hand.covering_count(suits)
        return self.op_match(math_inequality=math_expr, value=covering_count)


class BidComputer:
    """
    ════════════════════════════════════════════════════════════════════════════
    This class computes the bid to make when the rule which satisfied conditions
    provides a function to call instead of a bid.

    The unique method launches the function whose name is in Excel, in column
    function_bid, and sends argument written in column arg_bid if any.

    Properties
    hand:          The current player's hand, for who a bid should be decided.
    record:        All bids made since the game starts.
    haze:          Information on each player's hand deducted from bidding.
    ════════════════════════════════════════════════════════════════════════════
    """

    def __init__(self, hand: RichHand, record: BidRecord, haze: Haze):
        self.record = record
        self.hand = hand
        self.haze = haze

    def run(self, function_bid: str, arg: str = "") -> str:
        function_name = "_" + function_bid
        bid_runner = getattr(self, function_name)
        return bid_runner(arg)

    def _long_suit(self, arg: str) -> str:
        suit_rank = int(arg[-1]) - 1
        level_str = arg[0]
        suit_code = self.hand.longest_suits[suit_rank].code
        return level_str + suit_code

    def _support(self, level_str: str) -> str:
        partner_suit = self.record.second_last.suit
        return level_str + partner_suit.code

    def _cuebid(self, level_str: str) -> str:
        opp_camp = self.record.last.camp
        return level_str + self.record.last_suit_code(opp_camp)

    def _best_minor(self, level: str) -> str:
        return level + self.hand.best_minor_code

    def _best_major(self, level: str) -> str:
        return level + self.hand.best_major_code

    def _strength(self, level: str) -> str | None:
        camp_suits = self.record.suit_codes(self.record.second_last.camp)
        for suit in self.hand.strong_suits:
            if suit.code not in camp_suits:
                return level + suit.code
        return None

    def _short_suit(self, level: str) -> str | None:
        for suit, length in self.hand.cards_count.items():
            if length <= 1:
                return level + suit.code
        return None

    def _best_bi_suit(self, arg: str) -> str:
        """
        This function returns longest of given suits at given level.
        arg = pC[q]D with p:level, C:suit1, q:level2, D:suit2.
        when level2 is omitted, same level is applied for both suits.
        When suits have same length, choose the one with lowest level;
        If same level, choose lowest suit.
        """
        level1 = arg[0]
        level2 = arg[2] if arg[2].isnumeric() else level1
        suit1 = MetaSuit.from_code(arg[1])
        suit2 = MetaSuit.from_code(arg[-1])
        length_gap = self.hand.cards_count[suit1] - self.hand.cards_count[suit2]
        if length_gap > 0 or (length_gap == 0 and level1 <= level2):
            return level1 + suit1.code
        elif length_gap < 0 or (length_gap == 0 and level2 < level1):
            return level2 + suit2.code
        else:
            # case same length and same level
            return level1 + suit1.code if suit1 < suit2 else level2 + suit2.code

    def _unnamed_longest(self, arg: str) -> str:
        """
        This function returns bid with player's longest suit except opp suits,
        with a jump if arg is jump, or without if arg is no_jump.
        """
        jump: bool = arg == "jump"
        opp_suit_codes = self.record.suit_codes(self.record.last.camp)
        takeout_double = TakeoutDouble(self.hand.cards_count, opp_suit_codes)
        return takeout_double.answer(self.record.last_normal_bid(), jump)

    def _first_control(self, level: str) -> str:
        partner_bid = self.record.second_last
        fit = self.haze.fit(self.hand.cards_count, partner_bid.rank)
        camp_points = self.hand.points_HLD(fit.suit, fit.partner_count)
        bid_to_exceed = self.record.last_normal_bid()
        # First control must be at level 4 when level is 4, else it can be 3P
        if level == "4" and bid_to_exceed < Bid("3P"):
            bid_to_exceed = Bid("3P")

        slam = Slam(partner_bid.camp, fit.suit, fit.total_cards, camp_points, partner_bid)
        bid_sense = slam.next_bid(self.hand, self.record.second_last, bid_to_exceed, set())
        return bid_sense.raw_bid
