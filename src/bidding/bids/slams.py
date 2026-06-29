from __future__ import annotations

from enum import Enum
from functools import cached_property
from bridgebots import Rank
from bids.hands import RichHand, MetaSuit
from bids.bids import Bid
from bids.bid_senses import BidSense


PASS = "passe"


class Slam:
   """
   This class concerns players of the same camp who envisage a slam (chelem)
   using a suit as trump.
   It calculates next bid to make by this camp, considering that opposit camp
   IS PASSING.
   
   Properties
   trump:               Trump suit for which camp players are fitted.
   trumps_count:        Number of trump cards the camp has.
   camp_points:         Min HLD points for camp.
   ctrlled_suit_codes:  Suit codes the players declared control on except fit suit.
   ask_for_queen_bid:   The bid made to ask if the partner has trump queen.
   stage:               Stage in blackwood process.
   _cached_bids:        CONTROLS mapped in bids, excluding trump suit. 
   """
   CONTROLS = [
      "3P",
      "4T",
      "4K",
      "4C",
      "4P",
   ]
   BLACKWOOD = [
      "5T",
      "5K",
      "5C",
      "5P",
   ]
   class Stage(Enum):
      CTRLS = 0
      KEYS_ASK = 1,
      KEYS_R = 2,    # response
      QUEEN_ASK = 3,
      QUEEN_R = 4,   # response
      STOP = 5

   def __init__(self, trump: MetaSuit, camp_nbr_trumps: int, camp_points: int):
      self.trump = trump
      self.trumps_count = camp_nbr_trumps
      self.camp_points = camp_points
      self.ask_for_queen_bid: Bid = None
      self.stage = self.Stage.CTRLS

   @cached_property
   def _ctrl_bids(self) -> list[Bid]:
      return [Bid(r) for r in self.CONTROLS if r[1] != self.trump.code]

   def next_bid(self, hand: RichHand, partner_raw_bid: str, ctrls: set) -> BidSense:
      # Arg ctrls gives suit codes that the camp has declared as control.
      partner_bid = Bid(partner_raw_bid)
      match self.stage:
         case self.Stage.STOP:
            return BidSense.passe()
         case self.Stage.CTRLS:
            return self.next_control(hand, partner_bid, ctrls)
         case self.Stage.KEYS_ASK:
            return self._blackwood_answer(hand)
         case self.Stage.KEYS_R:
            return self._blackwood_redemand(hand, partner_bid)
         case self.Stage.QUEEN_ASK:
            return self._queen_answer(hand, partner_bid)
         case self.Stage.QUEEN_R:
            return self._bid_after_queen_answer(hand, partner_bid)

   def next_control(self, hand: RichHand, partner_bid: Bid, ctrls: set) -> BidSense:
      # Arg ctrls gives suit codes that the camp has declared as control.
      hand_ctrls: set[str] = hand.controlled_suit_codes()
      if ctrls | hand_ctrls | {self.trump.code} == set(MetaSuit.four_suit_codes()):
         # Camp has all controls
         if self._possible_level() >= 6:
            self.stage = self.Stage.KEYS_ASK
            return BidSense(id=0, raw_bid="4SA")
         else:
            return BidSense(id=0, raw_bid=self._trump_mini_bid(partner_bid))
      else:
         bid = self._new_ctrl(partner_bid, ctrls, hand_ctrls)
         raw_bid = bid.raw if bid else self._trump_mini_bid(partner_bid)
         return BidSense(id=0, raw_bid=raw_bid, suit_control=True)

   def _new_ctrl(self, partner_bid: Bid, ctrls: set, hand_ctrls: set) -> Bid:
      uncontrolled = self._remaining_controls(ctrls) - hand_ctrls
      hand_ctrls_not_declared = hand_ctrls - ctrls
      for bid in self._ctrl_bids:
         if bid < partner_bid:
            if bid.suit_code in uncontrolled and bid > self._ctrl_bids[0]:
               # A control is skipped and missing --> stop to game (manche):
               return None
         elif bid in hand_ctrls_not_declared:
            return bid

   def _blackwood_answer(self, hand: RichHand) -> BidSense:
         self.stage = self.Stage.KEYS_R
         nbr_keys, has_queen = hand.blackwood_keys(self.trump)
         index = 3 if has_queen and nbr_keys == 2 else nbr_keys % 3
         next_raw_bid = self.BLACKWOOD[index]
         return BidSense(id=0, raw_bid=next_raw_bid)
   
   def _blackwood_redemand(self, hand: RichHand, partner_bid: Bid) -> BidSense:
      camp_nbr_keys, camp_has_queen = self._get_camp_keys(hand, partner_bid.raw)
      if camp_nbr_keys <=3:
         next_raw_bid = self._trump_mini_bid(partner_bid)
      if camp_nbr_keys == 5:
         next_raw_bid = self._slam_bid(self._possible_level())
      # Camp has 4 keys:
      if self.trumps_count >= 9:
         next_raw_bid = self._slam_bid(self._possible_level())
      elif camp_has_queen:
         next_raw_bid = self._slam_bid(self._possible_level())
      else:
         next_raw_bid = self._ask_for_queen_bid(partner_bid)
      return BidSense(id=0, raw_bid=next_raw_bid)
      
   def _queen_answer(self, hand: RichHand, partner_bid: Bid) -> BidSense:
      """
      In case player has trump queen, this function returns most economical
      king suit if any, else little slam.
      When player does not have trump queen, this function returns a bid on
      trump at minimum level.
      See SEF page 65.
      """
      self.stage = self.Stage.QUEEN_R
      if hand.has_queen(self.trump):
         king_suit_code = self._get_most_economical_king_suit_wo_trump(hand)
         answer_suit_code = king_suit_code if king_suit_code else self.trump.code
         next_raw_bid = "6" + answer_suit_code
      else:
         next_raw_bid = partner_bid.first_bid_above_or_pass(self.trump).raw      
      return BidSense(id=0, raw_bid=next_raw_bid)

   def _bid_after_queen_answer(self, hand: RichHand, partner_bid: Bid) -> BidSense:
      self.stage = self.Stage.STOP
      partner_has_king = partner_bid.level == 6 and partner_bid.suit != self.trump
      if partner_has_king:
         ranks = hand.suits[partner_bid.suit]
         save_a_loss = len(ranks) >= 2 and ranks[0] in {Rank.ACE, Rank.QUEEN} \
            and ranks[1].value[0] <= 10
         next_raw_bid = ("7" if save_a_loss else "6") + self.trump.code
         return BidSense(id=0, raw_bid=next_raw_bid)
      else:
         return BidSense.passe()

   def _trump_mini_bid(self, partner_bid: Bid) -> str:
      self.stage = self.Stage.STOP
      return partner_bid.first_bid_above_or_pass(self.trump).raw
   
   def _slam_bid(self, level: int) -> str:
      self.stage = self.Stage.STOP
      return str(level) + self.trump.code

   def _possible_level(self) -> int:
      if self.camp_points >= 37:
         return 7
      elif self.camp_points >= 33:
         return 6
      else:
         return 5
      
   def _remaining_controls(self, ctrls: set[str]) -> set[str]:
      suits_wo_trump = [s for s in MetaSuit.four_suits() if s != self.trump]
      return set([s.code for s in suits_wo_trump if s.code not in ctrls])
   
   def _get_camp_keys(self, hand: RichHand, partner_raw_bid: str) -> tuple:
      # Returns (camp nbr of keys, True if the camp has trump queen else False)
      player_keys, player_queen = hand.blackwood_keys(self.trump)
      partner_queen = (self.BLACKWOOD.index(partner_raw_bid) == 3)
      partner_keys = 2 if partner_queen else self.BLACKWOOD.index(partner_raw_bid)
      partner_keys += 3 if player_keys + partner_keys < 3 else 0
      return (player_keys + partner_keys, player_queen or partner_queen)

   def _ask_for_queen_bid(self, partner_bid: Bid) -> str:
      next_bid = partner_bid.first_bid_above()
      if next_bid.suit == self.trump:
         next_bid = next_bid.first_bid_above()
      if next_bid.suit < self.trump:
         self.stage = self.Stage.QUEEN_ASK
         self.ask_for_queen_bid = next_bid
         return next_bid.raw
      else:
         return self._trump_mini_bid(partner_bid)

   def _get_most_economical_king_suit_wo_trump(self, hand: RichHand) -> str:
      # Returns lowest suit code except trump which has a king, from given hand.
      king_suits = hand.get_suits_having(Rank.KING)
      king_suits_wo_trump = list(filter(lambda s: s != self.trump, king_suits))
      return king_suits_wo_trump[0].code if king_suits_wo_trump else ""