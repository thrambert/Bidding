"""
This module manages the bidding phase for the distributed deal.
It starts with the dealer, then it passes to the next player in a
clockwise direction, and stops after 3 PASS.
"""
from bridgebots import Deal, Direction
from models.bid_rules import BidRule
from models.points import PointZone, matching
from models.hands import RichHand, SuitMeta
from models.bidding_records import Bidding


class BidMaker:
   def __init__(self, deal: Deal):
      self.deal = deal
      self.suit_meta = SuitMeta()
      self.bidding_record = []
      self.situation = "ouverture"
      self.sequence = ""
      self.player_position = "BID01"
      self.hand = RichHand(deal.hands[deal.dealer])
      self.direction: Direction = deal.dealer

   def relative_vuln(self) -> int:
      # returns -1 :unfavorable vulnerability, 0: neutral, 1: favorable.
      if self.direction in [Direction.NORTH, Direction.SOUTH]:
         return int(self.deal.ew_vulnerable) - int(self.deal.ns_vulnerable)
      else:
         return int(self.deal.ns_vulnerable) - int(self.deal.ew_vulnerable)

   def run_all(self):
       self.run_step()
       # TODO: create a loop
       pass

   def run_step(self):
      print(f"Main analysée {self.hand}")
      rules = BidRule.get_rules(self.situation, self.sequence)
      for rule in rules:
         print(f"--> rule {rule.id}")
         if self._is_rule_satisfied(rule):
            # TODO: next line to be completed
            # bidding = Bidding()
            print(f"      => The whole rule {rule.id} is satisfied.")

   def _is_rule_satisfied(self, rule: BidRule) -> bool:
      # for condition_name in Rule.condition_names():
      for condition_name in BidRule.condition_names()[:11]:
         if getattr(rule, condition_name):
            function_name = "_" + condition_name + "_check"
            if not globals()[function_name](self, rule):
               return False
            print(f"      {condition_name} \"{getattr(rule, condition_name)}\" is ok")
      return True


# ═══════════════════════════════════════════════════════════════════════════════
#  RULE CONDITIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _position_check(bid_maker: BidMaker, rule: BidRule) -> bool:
   return bid_maker.player_position == rule.position

def _points_check(bid_maker: BidMaker, rule: BidRule) -> bool:
   point_zone = PointZone(rule.points)
   if point_zone.is_HLD():
      return point_zone.contains_HLD(bid_maker.hand.points_HLD())
   else:
      return point_zone.contains(bid_maker.hand.points_H, bid_maker.hand.points_HL)
   
def _distribution_check(bid_maker: BidMaker, rule: BidRule) -> bool:
   return rule.distribution in bid_maker.hand.distribution

def _bicolor_check(bid_maker: BidMaker, rule: BidRule) -> bool:
   suits_fr: list = rule.bicolor.split(",")
   requested_suits = [bid_maker.suit_meta.FR_SUIT[s] for s in suits_fr]
   return all(s in bid_maker.hand.longest_suits for s in requested_suits)

def _color1_check(bid_maker: BidMaker, rule: BidRule) -> bool:
   player_longest = bid_maker.hand.longest_suits[0]
   return rule.color1 in bid_maker.suit_meta.any_names_fr(player_longest)

def _color1_count_check(bid_maker: BidMaker, rule: BidRule) -> bool:
   return matching(rule.color1_count, bid_maker.hand.count_longest[0])

def _color2_check(bid_maker: BidMaker, rule: BidRule) -> bool:
   player_2nd_longest = bid_maker.hand.longest_suits[1]
   return rule.color2 in bid_maker.suit_meta.any_names_fr(player_2nd_longest)

def _color2_count_check(bid_maker: BidMaker, rule: BidRule) -> bool:
   return matching(rule.color2_count, bid_maker.hand.count_longest[1])

def _won_tricks_check(bid_maker: BidMaker, rule: BidRule) -> bool:
   return bid_maker.hand.won_tricks >= rule.won_tricks

def _def_tricks_check(bid_maker: BidMaker, rule: BidRule) -> bool:
   return matching(rule.def_tricks, bid_maker.hand.def_tricks)

def _lost_tricks_check(bid_maker: BidMaker, rule: BidRule) -> bool:
   max_allowed_lost_tricks = rule.lost_tricks + bid_maker.relative_vuln()
   return bid_maker.hand.lost_tricks <= max_allowed_lost_tricks