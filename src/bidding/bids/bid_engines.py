"""
This module manages the bidding phase for the distributed deal.
It starts with the dealer, then it passes to the next player in a
clockwise direction, and stops after 3 passes.
"""
from bridgebots.deal import PlayerHand
from bids.bid_rules import BidRule
from bids.points import PointZone
from bids.hands import RichHand, MetaSuit
from bids.bids import Bid, SuitsToStop
from bids.bid_records import BidRecord
from bids.bid_senses import BidSense
from bids.bid_producers import BidProducer
from bids.hazes import Haze
from bids.slams import Slam
from bids.steps import Stair


PASS = "passe"


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
   _camps_step:   A set of tuples (n, str) where n is concerned player rank,
                  and str is next_step from Excel rules, or ""
   """
   def __init__(self):
      self.hand: RichHand = None
      self.relative_vuln = 0
      self.player_rank = 1
      self.record = BidRecord()
      self.haze = Haze()
      self.producer: BidProducer = None
      self.stair = Stair()

   def provide_bid(self, hand: PlayerHand, relative_vuln: int) -> BidSense:
      # This function returns bid the player has to make as a BidSense instance
      #  in which properties may be empty except bid if no sense to provide.
      self.hand = RichHand(hand)
      self.relative_vuln = relative_vuln
      _, self.player_rank = self.record.next_lap_and_rank(False)
      step = self._get_next_step()
      sense = self._get_next_bid(step)

      if not sense:
         print("ALERT Sense is None, and step is", step)

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
         if self.producer == None:
            self.producer = BidProducer(self.haze)
         return self.producer.make_bid(self.hand, self.record)
      else:
         return self._run_step(step)

   def _get_next_step(self) -> str:
      if self.record.last:
         return self.stair.get_next(
            self.record.last.raw, self.record.last.lap, self.player_rank,
            self.record.sleep(),
            self.record.nbr_interventions()
            )
      else:
         return self.stair.get_next("", 0, 1, False, 0)

   def _run_step(self, step_name: str) -> BidSense:
      # print(f"Step {step_name}")
      rule = self._get_first_satisfied_rule(step_name)
      self.stair.set_camp_next_step(rule.next_step if rule else "")
      if rule:
         return self._get_bid_sense(rule)
      else:
         return BidSense.passe()
   
   def _get_bid_sense(self, rule: BidRule) -> BidSense:
      if rule.sense_id:
         sense = BidSense.get(rule.sense_id)
         sense.raw_bid = rule.raw_bid
      else:
         sense = BidSense(id=0, raw_bid=rule.raw_bid)
      sense._rule_id = rule.id
      return sense

   def _get_first_satisfied_rule(self, step_name: str) -> BidRule:
      # Returns first satisfied rule in which raw_bid is computed with
      #  function_bid if required. If no rule satisfies, returns None.
      rules = BidRule.get_rules(step_name)
      analyzer = RuleAnalyzer(self.hand, self.relative_vuln, self.record, self.haze)
      for rule in rules:
         if analyzer.rule_satisfied(rule):
            # print(f"--> rule {rule.id} is fully satisfied.")
            return rule
            

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

   def rule_satisfied(self, rule: BidRule) -> bool:
      """
      This mutating function modifies rule to load raw_bid from function_bid,
      and returns True if conditions are satisfied and if computed bid is higher
      than last bid made.
      """
      for condition_name in BidRule.condition_names():
         # if attribute is not empty in rule instance:
         if getattr(rule, condition_name):
            function_name = "_" + condition_name + "_check"
            condition_check = getattr(self, function_name)
            if not condition_check(rule):
               return False
      if not rule.raw_bid:
         rule.raw_bid = self._compute_bid(rule.function_bid, rule.arg_bid) 
      bid = Bid(rule.raw_bid)
      return self.record.no_open() or bid.a_special \
         or self.record.last_normal_bid() < bid
   
   def _compute_bid(self, function_bid: str, arg: str) -> str:
      bid_computer = BidComputer(self.hand, self.record, self.haze)
      raw_bid = bid_computer.run(function_bid, arg)
      return raw_bid

   def op_match(self, math_inequality: str, value: int) -> bool:
      """
      Value and math inequality (<n, <=n, >n, >=n, =n, n) are concatenate to get a
      math expression, example: 'value<=n'.
      If math inequality is only a number, '==' is added in between.
      If inequality is one '=', it is changed into '=='.
      The math expression is then evaluated.
      """
      if math_inequality[0].isdigit():
         expression = str(value) + "==" + math_inequality
      elif math_inequality[0] == "=" and math_inequality[1].isdigit():
         expression = str(value) + "=" + math_inequality
      else:
         expression = str(value) + math_inequality
      return eval(expression)

   #  Basic conditions

   def _points_check(self, rule: BidRule) -> bool:
      point_zone = PointZone(rule.points)
      if point_zone.is_HLD():
         return point_zone.contains_HLD(self._get_player_HLD())
      else:
         return point_zone.contains(self.hand.points_H, self.hand.points_HL)
   
   def _get_player_HLD(self) -> int:
      fit = self.haze.fit(self.hand.cards_count, self.record.second_last.rank)
      if fit:
         return self.hand.points_HLD(fit.suit, fit.counts[0])
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
      max_allowed_lost_tricks = rule.lost_tricks + self.relative_vuln
      return self.hand.lost_tricks <= max_allowed_lost_tricks

   def _fit_cards_check(self, rule: BidRule) -> bool:
      if self.record.second_last:
         partner_suit = self.record.second_last.suit
         if partner_suit and partner_suit != MetaSuit.NO_TRUMP:
            player_cards_count = self.hand.cards_count[partner_suit]
            return self.op_match(rule.fit_cards, player_cards_count)

   def _stops_check(self, rule: BidRule) -> bool:
      opp_camp = self.record.last.camp
      opp_last_suit_code = self.record.last_suit_code(opp_camp)
      if opp_last_suit_code:
         suit = MetaSuit.from_code(opp_last_suit_code)
         return self.hand.stops_count(suit) >= 1
      else:
         return True
   
   def _awake_check(self, rule: BidRule) -> bool:
      if rule.awake:
         return self.record.last_pass_count() == 2
      else:
         return True
         
   def _hist_bid_check(self, rule: BidRule) -> bool:
      requested_raw_bids = list(reversed(rule.hist_bid.split(" ")))
      requested_bids = [Bid(value) for value in requested_raw_bids]
      return self.record.comply_with(requested_bids)


   #  Conditions as functions

   def _function1_check(self, rule: BidRule) -> bool:
      function_name = "_" + rule.function1 + "_check"
      condition_check = getattr(self, function_name)
      return condition_check()

   def _function2_check(self, rule: BidRule) -> bool:
      function_name = "_" + rule.function2 + "_check"
      condition_check = getattr(self, function_name)
      return condition_check(rule.arg2)

   def _no_good_major_5_check(self) -> bool:
      longest_suit = self.hand.longest_suits[0]
      if longest_suit.is_major:
         if self.hand.count_longest[0] == 5:
            if self.hand.suit_points_H(longest_suit) >= 6:
               return False
      return True

   def _major_4_check(self) -> bool:
      majors_4 = [n for n in self.hand.majors_count.values() if n == 4]
      return (len(majors_4) >= 1)

   def _any_short_color_check(self) -> bool:
      suit_lengths = sorted(self.hand.cards_count.values(), reverse=True)
      return suit_lengths[0] <= 1

   def _short_in_interv_color_check(self) -> bool:
      intervention_suit = MetaSuit.from_code(self.record.last.suit_code)
      return self.hand.cards_count[intervention_suit] <= 1

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

   def _takeout_double_check(self) -> bool:
      # Returns True if distribution is ok for a takeout double (contre d'appel)
      opp_camp = self.record.last.camp
      opp_codes = self.record.suit_codes(opp_camp)
      requested_suits = [s for s in MetaSuit.four_suits() if s.code not in opp_codes]
      majors_cards = []
      for suit in requested_suits:
         suit_cards_count = self.hand.cards_count[suit]
         if suit_cards_count < 3:
            return False
         if suit.is_major():
            majors_cards.append(suit_cards_count)
      if len(majors_cards) == 2:
         return majors_cards[0] + majors_cards[1] >= 7
      elif len(majors_cards) == 1:
         return majors_cards[0] >= 4
      else:
         return True

   def _suit_length_check(self, arg: str) -> bool:
      meta_suit = MetaSuit.from_code(arg[0])
      suit_length = self.hand.cards_count[meta_suit]
      condition = arg[1:]
      return self.op_match(math_inequality=condition, value=suit_length)

   def _longest_major_check(self, arg: str) -> bool:
      longest_count = max(self.hand.majors_count.values())
      return self.op_match(math_inequality=arg, value=longest_count)

   def _majors_at_least_4_check(self, arg: str) -> bool:
      majors_at_least_4 = [n for n in self.hand.majors_count.values() if n >= 4]
      count = len(majors_at_least_4)
      return self.op_match(math_inequality=arg, value=count)

   def _long_color_points_H_check(self, arg: str) -> bool:
      # n'importe quoi !
      longest_suit = self.hand.longest_suits[0]
      longest_suit_pts_H = self.hand.suit_points_H(longest_suit)
      return self.op_match(math_inequality=arg, value=longest_suit_pts_H)

   def _long_over_interv_check(self, arg: str) -> bool:
      over = (arg == "True")
      longest_suit = self.hand.longest_suits[0]
      interv_suit = MetaSuit.from_code(self.record.last.suit_code)
      return interv_suit < longest_suit if over else longest_suit < interv_suit

   def _stop_suit_check(self, arg: str) -> bool:
      suit = MetaSuit.from_code(arg)
      if suit:
         return self.hand.stops_count(suit) >= 1
      else:
         return False
      
   def _points_H_check(self, arg: str) -> bool:
      suit = MetaSuit.from_code(arg[0])
      math_expr = arg[1:]
      cards_count = self.hand.cards_count[suit]
      return self.op_match(math_inequality=math_expr, value=cards_count)

   def _control_check(self, arg: str) -> bool:
      suit = MetaSuit.from_code(arg)
      return self.hand.controls(suit)

   def _cards_gap_2_check(self, arg: str) -> bool:
      # Returns true if nbr cards in suit C <= nbr D - 2
      # Expect arg as "C, D" where C and D are suit codes.
      suit_codes = arg.replace(" ","").split(",")
      suits = [MetaSuit.from_code(c) for c in suit_codes]
      card_counts = [self.hand.cards_count[s] for s in suits]
      return (card_counts[0] <= card_counts[1] - 2)


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
      opponent_on_right_bid = self.record.last
      if opponent_on_right_bid.a_color:
         opponents_suit_code = opponent_on_right_bid.suit_code
      else:
         opponent_on_left_bid = self.record.third_last
         opponents_suit_code = opponent_on_left_bid.suit_code
      return level_str + opponents_suit_code

   def _best_minor(self, level: str) -> str:
      return level + self.hand.best_minor_code

   def _best_major(self, level: str) -> str:
      return level + self.hand.best_major_code

   def _first_control(self, arg: str) -> str:
      fit = self.haze.fit(self.hand.cards_count, self.record.second_last.rank)
      camp_points = self.hand.points_HLD(fit.suit, fit.partner_count())
      slam = Slam(fit.suit, fit.total_cards, camp_points)
      bid_sense = slam.next_control(self.hand, self.record.second_last, set())
      return bid_sense.raw_bid