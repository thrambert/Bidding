"""
This module represents the play mat with hands of 4 players, bidding boxes,
announced bids and played tricks.

So far, it only manages bid chaining. Later this module shall be integrated
in or called by a UI module.
"""
from bridgebots.deal import Deal
from bridgebots.deal_enums import Direction
from bids.bid_engines import BidEngine
from bids.bid_senses import BidSense
from bids.hands import RichHand
from bids.bid_histories import BidHistory
from utils import MyDataException


PASS = "passe"


class BidChaining:
   """
   This class successively considers player's hand to determine which bid make.
   It starts from the dealer, then go to the next player in a clockwise
   direction, and stops after 3 passes.

   Properties
   deal:             The given deal.
   current_player:   Current player's direction.
   bid_chain:        Biddings made by each player.
   _pass_count:      Number of consecutive pass made in last bids.
   _bid_engine:      Instance of engine class.
   """
   def __init__(self, deal: Deal):
      self.deal = deal
      self.current_player: Direction = deal.dealer
      self.bid_chain: dict[Direction, list[BidSense]] = {d: [] for d in Direction}
      self._pass_count = 0
      self._bid_engine = BidEngine()

   def run(self):
      # This function is used for test only. In real life, UI will ask for a bid.
      print()
      print(self._deal_cards_repr())
      print("="*80)

      count = 0
      while not self._bidding_completed():
         count += 1
         if count > 30:
            raise MyDataException("Too many bids for same deal !")
         
         player_hand = self.deal.hands[self.current_player]
         bid_sense = self._bid_engine.provide_bid(player_hand, self._relative_vuln())

         pbid = "-" if bid_sense.raw_bid == "passe" else bid_sense.raw_bid
         print(f"{self.current_player.name:<5}  {pbid:<3}   ", f"sense {bid_sense.id}" if bid_sense.id else "")

         self._pass_count = self._pass_count + 1 if bid_sense.raw_bid == PASS else 0
         self.bid_chain[self.current_player].append(bid_sense)
         self.current_player = self.current_player.next()

      self._write_satisfied_rule_ids_in_file()

   def _bidding_completed(self) -> bool:
      dealer_bids = self.bid_chain[self.deal.dealer]
      if len(dealer_bids) == 1 and dealer_bids[0].raw_bid == PASS:
         return self._pass_count == 4
      else:
         return self._pass_count == 3

   def _relative_vuln(self) -> int:
      # returns -1 :unfavorable vulnerability, 0: neutral, 1: favorable.
      if self.current_player in [Direction.NORTH, Direction.SOUTH]:
         return int(self.deal.ew_vulnerable) - int(self.deal.ns_vulnerable)
      else:
         return int(self.deal.ns_vulnerable) - int(self.deal.ew_vulnerable)

   def _write_satisfied_rule_ids_in_file(self):
      bid_senses = self._get_bid_senses_chronology()
      rule_ids = [s._rule_id for s in bid_senses if s._rule_id]
      for id in rule_ids:
         bid_history = BidHistory(id=id)
         bid_history.add_in_file()

   def _get_bid_senses_chronology(self) -> list[BidSense]:
      bid_sense_history = []
      for i in range(0, 10):
         for dir in Direction:
            if i >= len(self.bid_chain[dir]):
               return bid_sense_history
            bid_sense_history.append(self.bid_chain[dir][i])

   def _deal_cards_repr(self) -> list[str]:
      # Returns list of rich hands repr sorted from North to West
      hands = [v for k, v in sorted(self.deal.hands.items(), key=lambda item: item[0])]
      rich_hands_repr = [f"{RichHand(h)}" for h in hands]
      return rich_hands_repr
   