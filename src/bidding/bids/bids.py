from __future__ import annotations

from enum import Enum
from bids.hands import MetaSuit


class SpecialBid(Enum):
   PASS =   "passe", "passe"
   X =      "X", "contre"
   XX =     "XX", "surcontre"

   def __init__(self, code, text):
      self.code = code
      self.text = text

   @staticmethod
   def all_values() -> list:
      return [b.code for b in SpecialBid]


class Camp(Enum):
   OPEN = (1, 3)
   INT = (2, 4)

   @classmethod
   def from_rank(cls, rank: int) -> Camp:
      return cls.OPEN if rank in Camp.OPEN.value else cls.INT

   def other_camp(self) -> Camp:
      return Camp.OPEN if self.name == Camp.INT.name else Camp.INT

   def contains(self, rank: int) -> bool:
      return rank in self.value
   
   def other_rank(self, rank: int) -> int:
      for rk in self.value:
         if rk != rank:
            return rk


class Bid:
   """
   This class manages bid and its component as level, suit, or special bid.
   
   Properties
   raw:        String raw value, Examples: 3SA, 4P, X, passe
   level:      Level of the bid. Example 3SA is level 3, PASSE is level 0.
   suit_code:  1 or 2 caps chr in french or "" for special bid. Examples: C, SA, M
   suit:       MetaSuit instance, or None if special bid or symbolic (M, m, E)
   a_color:    True if bid is related to spade, heart, diamond or club.
   a_special:  True if it is a special bid, means in enum SpecialBid.
   a_symbol:   True if suit_code is a symbolic suit code, see below.
   any_bid:    True if bid == "o" means it symbolize any bid including special bid.
   """
   SYMBOLIC_SUIT_CODES = [
      "M",  # Majeure
      "m",  # mineure
      "E",  # any of 4 colors
   ]
   SUIT_CODES_BY_GROUP = {
      "m": ["T", "K"],
      "M": ["C", "P"],
      "E": ["T", "K", "C", "P"]
   }

   def __init__(self, value: str):
      self.raw = value
      self.level = int(value[0]) if value[0].isdigit() else 0
      self.a_special = value in SpecialBid.all_values()
      self.suit_code = value[1:] if self.level >= 1 else ""
      self.suit = MetaSuit.from_code(self.suit_code) if self.suit_code else None
      self.a_color = self.suit and self.suit != MetaSuit.NO_TRUMP
      self.a_symbol = self.suit_code in self.SYMBOLIC_SUIT_CODES
      self.any_bid = value == "o"

   def __eq__(self, bid2) -> bool:
      return self.raw == bid2.raw
   
   def __hash__(self):
      return hash(self.raw)
   
   def __lt__(self, bid2) -> bool:
      if self.level == bid2.level:
         return self.suit <  bid2.suit
      else:
         return self.level < bid2.level

   def __gt__(self, bid2) -> bool:
      if self.level == bid2.level:
         return self.suit > bid2.suit
      else:
         return self.level > bid2.level

   def bid_match(self, other_bid: Bid) -> bool:
      if self.level != other_bid.level:
         return False
      if self.suit_code == other_bid.suit_code:
         return True
      if other_bid.any_bid:
         return True
      if other_bid.suit_code in self.SUIT_CODES_BY_GROUP.keys():
         return self.suit_code in self.SUIT_CODES_BY_GROUP[other_bid.suit_code]
      return False

   def first_bid_above(self) -> Bid:
      next_suit_rank = self.suit.rank + 1 if self.suit.rank < 3 else 0
      suit = MetaSuit.from_rank(next_suit_rank)
      level = self.level + (1 if next_suit_rank == 0 else 0)
      return Bid(str(level) + suit.code)

   def first_bid_above_or_pass(self, suit: MetaSuit) -> Bid:
      # Returns a bid in given suit above self bid, or pass if self suit equals
      #  given suit.
      if suit == self.suit:
         return Bid(SpecialBid.PASS.code)
      level = self.level + (0 if self.suit < suit else 1)
      return Bid(str(level) + suit.code)

   def replace_suit_with(self, suit_code: str) -> Bid:
      # Returns a new bid in which suit code is replaced by given one
      if self.level:
         raw_bid = str(self.level) + suit_code
      else:
         raw_bid = self.raw
      return Bid(raw_bid)

   @staticmethod
   def valid_raw_bid(value: str) -> bool:
      bid = Bid(value)
      if bid.a_special or bid.any_bid:
         return True
      if not bid.level in range(1, 8):
         return False
      return bid.suit or bid.a_symbol


class Forcing(Enum):
   ONCE = "forcing"
   ROUND = "manche"
   AUTO = "autoforcing"
   PASS = "passe"

   @staticmethod
   def from_value(value: str) -> Forcing:
      for item in Forcing:
         if item.value == value:
            return item
   
   def __repr__(self) -> str:
      match self:
         case self.ONCE:
            return "forcing pour un tour"
         case self.ROUND:
            return "forcing de manche"
         case self.AUTO:
            return "forcing et autoforcing"
         case self.PASS:
            return "forcing passe"


class SuitsToStop(Enum):
   OPP = "opp"
   UNNAMED = "unnamed"

   @staticmethod
   def from_value(value: str) -> SuitsToStop:
      for item in SuitsToStop:
         if item.value == value:
            return item
