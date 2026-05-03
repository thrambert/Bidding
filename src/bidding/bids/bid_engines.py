"""
This module manages the bidding phase for the distributed deal.
It starts with the dealer, then it passes to the next player in a
clockwise direction, and stops after 3 passes.
"""
from bridgebots.deal import PlayerHand
from bids.bid_rules import BidRule
from bids.points import PointZone
from bids.hands import RichHand, MetaSuit
from bids.bid_records import Bidding, BidRecord
from bids.slams import Slam
import bids.steps as steps


PASS = "passe"


def op_match(math_inequality: str, value: int) -> bool:
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

class BidEngine:
   """
   This class is an engine to determine which bid a player should make.
   It remains active while players are bidding, and it stores each bid made
   into record property.
   It uses rules coming from Excel sheet, and it delegates the rules analyzis
   to an instance of class RuleAnalyzer.

   Properties
   record:        All bids made since the game starts.
   hand:          The current player's hand, for who a bid should be decided.
   slam:          An instance to manage bids sequences in a slam perspective.
   _next_step_open:  Next step given by Excel rules for opener's camp if any.
   """
   def __init__(self):
      self.record = BidRecord()
      self.hand: RichHand = None
      self.slam: Slam = None
      self._next_step_open = ""

   def define_bid(self, hand: PlayerHand) -> str:
      # This function returns bid value the current player has to make.
      self.hand = RichHand(hand)
      next_step = steps.get_next(
         last=self.record.last, 
         sleep=self.record.last_pass_count() == 2,
         intervene_count=self.record.get_intervention_count(),
         next_step_open=self._next_step_open
      )
      bidding = self._run_step(next_step)
      print("="*100)
      print(f"--> {bidding.lap}e tour, le joueur n°{bidding.rank} fait l'enchère {bidding.bid}")
      return bidding.bid

   def _run_step(self, step_name: str) -> Bidding:
      rule = self._get_first_satisfied_rule(step_name)
      rule_id = rule.id if rule else 0
      if rule:
         if rule.next_step_open:
            self._next_step_open = rule.next_step_open
         bid = rule.bid if rule.bid else self._compute_bid(rule.function_bid, rule.arg_bid)
      else:
         bid = PASS
      return self.record.add_bidding(bid, rule_id)
   
   def _get_first_satisfied_rule(self, step_name: str) -> BidRule:
      # Returns first satisfied rule or None.
      rules = BidRule.get_rules(step_name)
      analyzer = RuleAnalyzer(self.record, self.hand)
      for rule in rules:
         print(f"--> rule {rule.id}")
         if analyzer.rule_satisfied(rule):
            print(f"--> rule {rule.id} is fully satisfied.")
            return rule
            
   def _compute_bid(self, function_bid: str, arg: str) -> str:
      bid_computer = BidComputer(self.record, self.hand, self.slam)
      bid, object = bid_computer.run(function_bid, arg)
      if object and isinstance(object, Slam):
         self.slam = object
      return bid


class RuleAnalyzer:
   """
   ════════════════════════════════════════════════════════════════════════════
   This class examines rules for a given hand at a given stage of bidding.

   The unique public method checks all conditions contained in a rule to see if
   the rule is satisfied. It launches functions whose names are deducted from 
   header of Excel rules columns, and true if all conditions of a rule are
   satisfied. Conditions are Excel cells in row of given rule.
   ════════════════════════════════════════════════════════════════════════════
   """
   def __init__(self, record: BidRecord, hand: RichHand):
      self.record = record
      self.hand = hand

   def rule_satisfied(self, rule: BidRule) -> bool:
      for condition_name in BidRule.condition_names():
         # if attribute is not empty in rule instance:
         if getattr(rule, condition_name):
            function_name = "_" + condition_name + "_check"
            condition_check = getattr(self, function_name)
            if not condition_check(rule):
               return False
            print(f"      {condition_name} \"{getattr(rule, condition_name)}\" is ok")
      return True

   #  Basic conditions

   def _points_check(self, rule: BidRule) -> bool:
      point_zone = PointZone(rule.points)
      if point_zone.is_HLD():
         return point_zone.contains_HLD(self.hand.points_HLD())
      else:
         return point_zone.contains(self.hand.points_H, self.hand.points_HL)
      
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
      return op_match(rule.suit1_count, self.hand.count_longest[0])

   def _suit2_check(self, rule: BidRule) -> bool:
      player_2nd_longest_suit = self.hand.longest_suits[1]
      return rule.suit2 in player_2nd_longest_suit.any_texts()

   def _suit2_count_check(self, rule: BidRule) -> bool:
      return op_match(rule.suit2_count, self.hand.count_longest[1])

   def _first_pass_check(self, rule: BidRule) -> bool:
      return op_match(rule.first_pass, self.record.first_pass_count())

   def _won_tricks_check(self, rule: BidRule) -> bool:
      return self.hand.won_tricks >= rule.won_tricks

   def _def_tricks_check(self, rule: BidRule) -> bool:
      return op_match(rule.def_tricks, self.hand.def_tricks)

   def _lost_tricks_check(self, rule: BidRule) -> bool:
      max_allowed_lost_tricks = rule.lost_tricks + self.relative_vuln()
      return self.hand.lost_tricks <= max_allowed_lost_tricks

   def _fit_cards_check(self, rule: BidRule) -> bool:
      may_fit_suit_code = self.record.partner_last_suit_code()
      if may_fit_suit_code:
         meta_suit = MetaSuit.from_code(may_fit_suit_code)
         player_cards_count = self.hand.cards_count[meta_suit]
         return op_match(rule.fit_cards, player_cards_count)

   def _stops_check(self, rule: BidRule) -> bool:
      return True

   def _awake_check(self, rule: BidRule) -> bool:
      if rule.awake:
         return self.record.last_pass_count() == 2
      else:
         return True
         
   def _hist_bid_check(self, rule: BidRule) -> bool:
      requested_bids = list(reversed(rule.hist_bid.split(" ")))
      hist_bidding = self.record.reversed_all()
      if len(hist_bidding) < len(requested_bids):
         return False
      for i in range(0, len(requested_bids)):
         if not hist_bidding[i].bid_match(symbolic_bid=requested_bids[i]):
            return False
      return True

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
      return points_H_in_bicolors >= self.hand.points_H - 3

   def _honors_in_short_colors_check(self) -> bool:
      suits = [s for s, count in self.hand.cards_count.items() if count <= 2]
      for meta_suit in suits:
         if self.hand.suit_points_H(meta_suit) < 3:
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
      for suit_code in self.record.opponents_suit_codes():
         meta_suit = MetaSuit.from_code(suit_code)
         if not self.hand.stop_suit(meta_suit):
            return False
      return True

   def _takeout_double_check(self) -> bool:
      # Returns True if distribution is ok for a takeout double (contre d'appel)
      opp_codes = self.record.opponents_suit_codes()
      requested_suits = [s for s in MetaSuit if s.code not in opp_codes]
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
      return op_match(math_inequality=condition, value=suit_length)

   def _longest_major_check(self, arg: str) -> bool:
      longest_count = max(self.hand.majors_count.values())
      return op_match(math_inequality=arg, value=longest_count)

   def _majors_at_least_4_check(self, arg: str) -> bool:
      majors_at_least_4 = [n for n in self.hand.majors_count.values() if n >= 4]
      count = len(majors_at_least_4)
      return op_match(math_inequality=arg, value=count)

   def _long_color_points_H_check(self, arg: str) -> bool:
      longest_count = max(self.hand.count_longest[0])
      return op_match(math_inequality=arg, value=longest_count)

   def _long_over_interv_check(self, arg: str) -> bool:
      over = (arg == "True")
      longest_suit = self.hand.longest_suits[0]
      interv_suit = MetaSuit.from_code(self.record.last.suit_code)
      return interv_suit < longest_suit if over else longest_suit < interv_suit


class BidComputer:
   """
   ════════════════════════════════════════════════════════════════════════════
   This class computes the bid to make when the rule which satisfied conditions
   provides a function to call instead of a bid.

   The unique method launches the function whose name is in Excel, in column 
   function_bid, and sends argument written in column arg_bid if any.
   ════════════════════════════════════════════════════════════════════════════
   """
   def __init__(self, record: BidRecord, hand: RichHand, slam: Slam):
      self.record = record
      self.hand = hand
      self.slam = slam

   def run(self, function_bid: str, arg: str = "") -> tuple:
      # Returns (bid, object) where object may be None or slam instance.
      function_name = "_" + function_bid
      bid_runner = getattr(self, function_name)
      if function_bid == "control":
         return bid_runner(arg)
      else:
         return (bid_runner(arg), None)

   def _long_suit(self, arg: str) -> str:
      suit_rank = int(arg[-1]) - 1
      level_str = arg[0]
      suit_code = self.hand.longest_suits[suit_rank].code
      return level_str + suit_code

   def _support(self, level_str: str) -> str:
      partner_suit_code = self.record.partner_last_suit_code()
      return level_str + partner_suit_code

   def _cuebid(self, level_str: str) -> str:
      opponents_suit_code = self.record.opponent_on_right_suit_code()
      if not opponents_suit_code:
         opponents_suit_code = self.record.opponent_on_left_suit_code()
      return level_str + opponents_suit_code

   def _best_minor(self) -> str:
      return self.hand.best_minor_code

   def _best_major(self) -> str:
      return self.hand.best_major_code

   def _control(self, arg: str) -> tuple:
      # Returns (bid, object) where object is slam or None
      if  arg:
         data = arg.replace(" ", "").split(",")
         partner_suit_code = self.record.partner_last_suit_code()
         fit_suit_code = data.pop(0) if data[0].isalpha() else partner_suit_code
         players_HLD = [int(s) for s in data]
         splinter = partner_suit_code if self.record.partner_made_splinter() else ""
         slam = Slam(rank=self.record.next_rank, suit=fit_suit_code, 
                     pts_HLD=players_HLD, splinter=splinter)
         bid = slam.next_bid(self.partner_last_bid(), self.hand.controlled_suits())
         return (bid, slam)
