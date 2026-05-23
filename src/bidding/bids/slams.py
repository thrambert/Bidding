from __future__ import annotations

from enum import Enum
from bids.hands import RichHand, MetaSuit
from bids.bids import Bid, Camp
from bids.bid_senses import BidSense


PASS = "passe"


class Slam:
   """
   This class concerns players of the same camp who envisage a slam (chelem).
   It calculates next bid to make by this camp, considering that opposit camp
   is passing.
   
   Properties
   trump:               Trump suit for which camp players are fitted.
   trumps_count:        Number of trump cards the camp has.
   camp_points:         Min HLD points for camp.
   ctrlled_suit_codes:  Suit codes the players declared control on except fit suit.
   ask_for_queen_bid:   The bid made to ask if the partner has trump queen.
   stage:               Stage in blackwood process.
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

   def next_bid(self, hand: RichHand, partner_bid: Bid, ctrls: set) -> BidSense:
      # Arg ctrls gives suit codes that the camp has declared as control.
      match self.stage:
         case self.Stage.STOP:
            return BidSense.passe()
         case self.Stage.CTRLS:
            return self._next_control(hand, partner_bid, ctrls)
         case self.Stage.KEYS_ASK:
            return self._blackwood_answer(hand)
         case self.Stage.KEYS_R:
            return self._blackwood_redemand(hand, partner_bid)
         case self.Stage.QUEEN_ASK:
            return self._queen_answer(hand, partner_bid)
         case self.Stage.QUEEN_R:
            return self._bid_after_queen_answer(partner_bid, partner_rank)

   def _next_control(self, hand: RichHand, partner_bid: Bid, ctrls: set) -> BidSense:
      ctrls.discard(self.trump.code)
      if len(ctrls) == 3 and self._level() >= 6:
         self.stage = self.Stage.KEYS_ASK
         return BidSense(id=0, raw_bid="4SA")
      hand_ctrls = hand.controlled_suits()
      for bid in self._remaining_control_bids(ctrls):
         if bid.suit_code in hand_ctrls:
            return BidSense(id=0, raw_bid=bid.raw, suit_control=True)
         elif bid < partner_bid:
            # A control is skipped and missing --> stop to game (manche):
            self.stage = self.Stage.STOP
            next_bid = partner_bid.first_bid_above_or_pass(self.fit_suit_code)
            return BidSense(id=0, raw_bid=next_bid.raw)
      
   def _blackwood_answer(self, hand: RichHand) -> BidSense:
         self.stage = self.Stage.KEYS_R
         nbr_keys, has_queen = hand.blackwood_keys()
         index = 3 if has_queen and nbr_keys == 2 else nbr_keys % 3
         next_raw_bid = self.BLACKWOOD[index]
         return BidSense(id=0, raw_bid=next_raw_bid)
   
   def _blackwood_redemand(self, hand: RichHand, partner_bid: Bid) -> BidSense:
      camp_nbr_keys, camp_has_queen = self._get_camp_keys(hand, partner_bid.raw)
      if camp_nbr_keys <=3:
         next_raw_bid = self._trump_mini_bid(partner_bid)
      if camp_nbr_keys == 5:
         next_raw_bid = self._slam_bid(self._level())
      # Camp has 4 keys:
      if self.trumps_count >= 9:
         next_raw_bid = self._slam_bid(self._level())
      elif camp_has_queen:
         next_raw_bid = self._slam_bid(self._level())
      else:
         next_raw_bid = self._ask_for_queen_bid(partner_bid)
      return BidSense(id=0, raw_bid=next_raw_bid)
      
   
   def _queen_answer(self, hand: RichHand, partner_bid: Bid) -> BidSense:
      self.stage = self.Stage.QUEEN_R
      next_bid = partner_bid.first_bid_above()
      if hand.has_queen(self.fit.suit):
         next_bid = next_bid.first_bid_above()
      return BidSense(id=0, raw_bid=next_bid.raw)
   
   def _bid_after_queen_answer(self, partner_bid: Bid, rank: int) -> BidSense:
      sticked_bid = self.ask_for_queen_bid.first_bid_above()
      has_queen = (partner_bid != sticked_bid)
      if has_queen:
         next_raw_bid = self._slam_bid(self._level())
      else:
         next_raw_bid = self._trump_mini_bid(partner_bid)
      return BidSense(id=0, raw_bid=next_raw_bid)

   def _trump_mini_bid(self, partner_bid: Bid) -> str:
      self.stage = self.Stage.STOP
      return partner_bid.first_bid_above_or_pass(self.fit.suit).raw
   
   def _slam_bid(self, level: int) -> str:
      self.stage = self.Stage.STOP
      return str(level) + self.fit.code

   def _level(self) -> int:
      if self.camp_points >= 37:
         return 7
      elif self.camp_points >= 33:
         return 6
      else:
         return 5

   def _remaining_control_bids(self, ctrls: set[str]) -> list[Bid]:
      remaining_control_bids = []
      for bid in [Bid(c) for c in self.CONTROLS]:
         if not(bid.suit_code in ctrls or bid.suit == self.trump):
            remaining_control_bids.append(bid)
      return remaining_control_bids
      
   def _get_camp_keys(self, hand: RichHand, partner_raw_bid: str) -> tuple:
      # Returns (camp nbr of keys, True if the camp has trump queen else False)
      player_keys, player_queen = hand.blackwood_keys()
      partner_queen = (self.BLACKWOOD.index(partner_raw_bid) == 3)
      partner_keys = 2 if partner_queen else self.BLACKWOOD.index(partner_raw_bid)
      partner_keys += 3 if player_keys + partner_keys < 3 else 0
      return (player_keys + partner_keys, player_queen or partner_queen)

   def _ask_for_queen_bid(self, partner_bid: Bid) -> str:
      next_bid = partner_bid.first_bid_above()
      if next_bid.suit == self.fit.suit:
         next_bid = next_bid.first_bid_above()
      if next_bid.suit < self.fit.suit:
         self.stage = self.Stage.QUEEN_ASK
         self.ask_for_queen_bid = next_bid
         return next_bid.raw
      else:
         return self._trump_mini_bid(partner_bid)
      
      
# class Fit:
#    """
#    This class describes a fit in a suit that players of the same camp have
#    identified.
   
#    Properties
#    camp:       Camp of players who are concerned by the fit.
#    suit:       Suit for which these players are fitted.
#    code:       Suit code.
#    nbr_cards:  Dict player rank --> Nbr of fitted cards the player promised.
#    """
#    def __init__(self, camp: Camp, suit: str, players_nbr_cards: dict):
#       self.camp = camp
#       self.suit = MetaSuit.from_code(suit)
#       self.code = suit
#       self.nbr_cards = players_nbr_cards
   
#    def total_cards(self) -> int:
#       return sum(self.nbr_cards.values())
   
#    def _cards_gap(self) -> int:
#       return abs(self.nbr_cards[0] - self.nbr_cards[1])

#    @staticmethod
#    def get_best(fits: list[Fit]) -> Fit:
#       if len(fits) == 1:
#          return fits[0]
#       fit1, fit2 = fits[0], fits[1]
#       if fit1.suit.is_major() == fit2.suit.is_major():
#          if fit1.total_cards() == fit2.total_cards():
#             return fit1 if fit1._cards_gap() <= fit2._cards_gap() else fit2
#          else:
#             return fit1 if fit1.total_cards() > fit2.total_cards() else fit2
#       else:
#          return fit1 if fit1.suit.is_major() and fit1.total_cards() >= 8 else fit2


# class Slam:
#    """
#    This class concerns players of the same camp who envisage a slam (chelem).
#    It calculates next bid to make by this camp, considering that opposit camp
#    is passing.
   
#    Properties
#    camp:                Camp of players who are engaged in a slam process.
#    fit:                 Fit on a suit between the 2 players of the camp.
#    splinter_suit_code:  Suit code of the splinter if any. Unused so far (05-2026).
#    players_points:      Dict of min max HLD points, with player rank as dict key.
#    ctrlled_suit_codes:  Suit codes the players declared control on except fit suit.
#    ask_for_queen_bid:   The bid made to ask if the partner has trump queen.
#    stage:               Stage in blackwood process.
#    """
#    CONTROLS = [
#       "3P",
#       "4T",
#       "4K",
#       "4C",
#       "4P",
#    ]
#    BLACKWOOD = [
#       "5T",
#       "5K",
#       "5C",
#       "5P",
#    ]
#    class Stage(Enum):
#       CTRLS = 0
#       KEYS_ASK = 1,
#       KEYS_R = 2,    # response
#       QUEEN_ASK = 3,
#       QUEEN_R = 4,   # response
#       STOP = 5

#    def __init__(self, fit: Fit, pts: dict, splinter: str = ""):
#       self.camp = fit.camp
#       self.fit = fit
#       self.splinter_suit_code = splinter
#       self.players_points: dict[int: tuple[int, int]] = pts
#       self.ctrlled_suit_codes: set = {splinter} if splinter else {}
#       self.ask_for_queen_bid: Bid = None
#       self.stage = self.Stage.CTRLS

#    def next_bid(self, partner_bid: Bid, partner_rank: int, hand: RichHand) -> str:
#       match self.stage:
#          case self.Stage.STOP:
#             return PASS
#          case self.Stage.CTRLS:
#             return self._next_control(partner_bid, partner_rank, hand)
#          case self.Stage.KEYS_ASK:
#             return self._blackwood_answer(hand)
#          case self.Stage.KEYS_R:
#             return self._blackwood_redemand(partner_bid, partner_rank, hand)
#          case self.Stage.QUEEN_ASK:
#             return self._queen_answer(partner_bid, hand)
#          case self.Stage.QUEEN_R:
#             return self._bid_after_queen_answer(partner_bid, partner_rank)

#    def _next_control(self, partner_bid: Bid, rank: int, hand: RichHand) -> str:
#       hand_ctrls = hand.controlled_suits()
#       controls_ok = self.ctrlled_suit_codes.union(hand_ctrls)
#       if len(controls_ok) == 3 and self._level(rank) >= 6:
#          self.stage = self.Stage.KEYS_ASK
#          return "4SA"
#       for bid in self._remaining_control_bids():
#          if bid.suit_code in hand_ctrls:
#             # Next control
#             self.ctrlled_suit_codes.add(bid.suit_code)
#             return bid.raw
#          elif bid < partner_bid:
#             # A control is skipped and missing --> stop to game (manche):
#             self.stage = self.Stage.STOP
#             return partner_bid.first_bid_above_or_pass(self.fit_suit_code).raw
      
#    def _blackwood_answer(self, hand: RichHand) -> str:
#          self.stage = self.Stage.KEYS_R
#          nbr_keys, has_queen = hand.blackwood_keys()
#          index = 3 if has_queen and nbr_keys == 2 else nbr_keys % 3
#          return self.BLACKWOOD[index]
   
#    def _blackwood_redemand(self, partner_bid: Bid, rank: int, hand: RichHand) -> str:
#       camp_nbr_keys, camp_has_queen = self._get_camp_keys(partner_bid.raw, hand)
#       if camp_nbr_keys <=3:
#          return self._trump_mini_bid(partner_bid)
#       if camp_nbr_keys == 5:
#          return self._slam_bid(self._level(rank))
#       # Camp has 4 keys:
#       camp_nbr_trumps = self.fit.nbr_cards[rank] + hand.cards_count[self.fit.suit]
#       if camp_nbr_trumps >= 9:
#          return self._slam_bid(self._level(rank))
#       elif camp_has_queen:
#          return self._slam_bid(self._level(rank))
#       else:
#          return self._ask_for_queen_bid(partner_bid)
   
#    def _queen_answer(self, partner_bid: Bid, hand: RichHand) -> str:
#       self.stage = self.Stage.QUEEN_R
#       next_bid = partner_bid.first_bid_above()
#       if hand.has_queen(self.fit.suit):
#          next_bid = next_bid.first_bid_above()
#       return next_bid.raw
   
#    def _bid_after_queen_answer(self, partner_bid: Bid, rank: int) -> str:
#       sticked_bid = self.ask_for_queen_bid.first_bid_above()
#       has_queen = (partner_bid != sticked_bid)
#       if has_queen:
#          return self._slam_bid(self._level(rank))
#       else:
#          return self._trump_mini_bid(partner_bid)

#    def _trump_mini_bid(self, partner_bid: Bid) -> str:
#       self.stage = self.Stage.STOP
#       return partner_bid.first_bid_above_or_pass(self.fit.suit).raw
   
#    def _slam_bid(self, level: int) -> str:
#       self.stage = self.Stage.STOP
#       return str(level) + self.fit.code

#    def _level(self, partner_rank: int) -> int:
#       player_rank = self.camp.other_rank(partner_rank)
#       player_HLD = self.hand.points_HLD(self.fit.code, self.fit.nbr_cards[player_rank])
#       partner_HLD, _ = self.players_points[partner_rank]
#       camp_min_points = partner_HLD + player_HLD
#       if camp_min_points >= 37:
#          return 7
#       elif camp_min_points >= 33:
#          return 6
#       else:
#          return 5

#    def _remaining_control_bids(self) -> list[Bid]:
#       remaining_control_bids = []
#       for bid in [Bid(c) for c in self.CONTROLS]:
#          if bid.suit_code in self.ctrlled_suit_codes or bid.meta_suit == self.fit.suit:
#             continue
#          remaining_control_bids.append(bid)
#       return remaining_control_bids
      
#    def _get_camp_keys(self, hand: RichHand, partner_raw_bid: str) -> tuple:
#       # Returns (camp nbr of keys, True if the camp has trump queen else False)
#       player_keys, player_queen = hand.blackwood_keys()
#       partner_queen = (self.BLACKWOOD.index(partner_raw_bid) == 3)
#       partner_keys = 2 if partner_queen else self.BLACKWOOD.index(partner_raw_bid)
#       partner_keys += 3 if player_keys + partner_keys < 3 else 0
#       return (player_keys + partner_keys, player_queen or partner_queen)

#    def _ask_for_queen_bid(self, partner_bid: Bid) -> str:
#       next_bid = partner_bid.first_bid_above()
#       if next_bid.meta_suit == self.fit.suit:
#          next_bid = next_bid.first_bid_above()
#       if next_bid.meta_suit < self.fit.suit:
#          self.stage = self.Stage.QUEEN_ASK
#          self.ask_for_queen_bid = next_bid
#          return next_bid.raw
#       else:
#          return self._trump_mini_bid(partner_bid)