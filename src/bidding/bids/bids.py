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

   def contains(self, rank: int) -> bool:
      return rank in self.value


class Bid:
   """
   This class manages bid and its component as level, suit, or special bid.
   
   Properties
   raw:        String raw value, Examples: 3SA, 4P, X, passe
   level:      Level of the bid. Example 3SA is level 3, PASSE is level 0.
   suit_code:  1 or 2 caps chr in french or "" for special bid. Examples: C, SA.
   meta_suit:  MetaSuit instance, or None if special bid.
   a_color:    True if bid is related to spade, heart, diamond or club.
   a_special:  True if it is a special bid.
   """
   SYMBOLIC_SUIT_CODES = [
      "T",
      "K",
      "C",
      "P",
      "M",  # Majeure
      "m",  # mineure
      "E",  # any of 4 colors
      "SA",
   ]
   SUIT_CODES_BY_GROUP = {
      "m": ["T", "K"],
      "M": ["C", "P"],
   }

   def __init__(self, value: str):
      self.raw = value
      self.level = int(value[0]) if value[0].isdigit() else 0
      self.a_special = value in SpecialBid.all_values()
      self.suit_code = value[1:] if self.level >= 1 else ""
      self.meta_suit = MetaSuit.from_code(self.suit_code) if self.suit_code else None
      self.a_color = not self.suit_code in ["", "SA"]

   def __eq__(self, bid2) -> bool:
      return self.raw == bid2.raw
   
   def __hash__(self):
      return hash(self.raw)
   
   def __lt__(self, bid2) -> bool:
      if self.level == bid2.level:
         return self.meta_suit <  bid2.meta_suit
      else:
         return self.level < bid2.level

   def bid_match(self, symbolic_bid: str) -> bool:
      if self.raw == symbolic_bid:
         return True
      if self.level != int(symbolic_bid[0]):
         return False
      return self.suit_code in self.SUIT_CODES_BY_GROUP[symbolic_bid[1:]]

   def first_bid_value_above_for(self, meta_suit: MetaSuit) -> str:
      # Returns a bid value in given suit just above self bid
      level = self.level + (0 if self.meta_suit > meta_suit else 1)
      return str(level) + meta_suit.code

   @staticmethod
   def valid_symbolic_bid(value: str) -> bool:
      if value in [b.code for b in SpecialBid]:
         return True
      level = int(value[0]) if value[0].isdigit() else 0
      suit_code = value[1:] if level >= 1 else ""
      return level in range(1, 8) and suit_code in Bid.SYMBOLIC_SUIT_CODES


class Forcing(Enum):
   ONCE = "forcing"
   ROUND = "manche"
   AUTO = "autoforcing"
   PASS = "passe"

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


