"""
This module represents the play mat with hands of 4 players, bidding boxes,
announced bids and played tricks.

By the way, and for testing purpose, it only manages chaining bidding.
"""
from bridgebots.deal import Deal
from bridgebots.deal_enums import Direction
from bids.bid_engines import BidEngine


PASS = "passe"


class BidChaining:
   """
   This class successively considers player's hand to determine which bid make.
   It starts from the dealer, then go to the next player in a clockwise
   direction, and stops after 3 passes.

   Properties
   deal:             The given deal.
   current_player:   Current player's direction.
   bidding:          Bids made by each player.
   _pass_count:      Number of consecutive pass made in last bids.
   _bid_engine:      Instance of engine class.
   """
   def __init__(self, deal: Deal):
      self.deal = deal
      self.current_player: Direction = deal.dealer
      self.bidding = {d: [] for d in Direction}
      self._pass_count = 0
      self._bid_engine = BidEngine()

   def run_all(self):
      # This function is used for test only. In real life, UI will ask for a bid.
      while not self._bidding_completed():
         player_hand = self.deal.hands[self.current_player]
         bid_value = self._bid_engine.define_bid(player_hand)
         self._pass_count = self._pass_count + 1 if bid_value == PASS else 0
         self.bidding[self.current_player].append(bid_value)
         self.current_player = self.current_player.next()
      print(f"\nFin des enchères")
      print("="*100)

   def _bidding_completed(self) -> bool:
      dealer_bids = self.bidding[self.deal.dealer]
      if len(dealer_bids) == 1 and dealer_bids[0] == PASS:
         return self._pass_count == 4
      else:
         return self._pass_count == 3

   def _relative_vuln(self) -> int:
      # returns -1 :unfavorable vulnerability, 0: neutral, 1: favorable.
      if self.current_player in [Direction.NORTH, Direction.SOUTH]:
         return int(self.deal.ew_vulnerable) - int(self.deal.ns_vulnerable)
      else:
         return int(self.deal.ns_vulnerable) - int(self.deal.ew_vulnerable)

