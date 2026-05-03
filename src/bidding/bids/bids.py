from enum import Enum


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


class Bid:
   """
   This class manages bid and its component as level, suit, or special bid.
   
   Properties
   value:      String raw value, Examples: 3SA, 4P, X, passe
   level:      Level of the bid. Example 3SA is level 3, PASSE is level 0.
   suit_code:  1 or 2 caps chr in french or "" for special bid. Examples: C, SA.
   suit:       Suit, or None if special bid.
   a_color:    True if bid is related to spade, heart, diamond or club.
   a_special:  True if it is a special bid.
   """
   def __init__(self, value: str):
      self.value = value
      self.level = int(value[0]) if value[0].isdigit() else 0
      self.a_special = value in SpecialBid.all_values()
      self.suit_code = value[1:] if self.level >= 1 and self.is_special else ""
      self.a_color = not self.suit_code in ["", "SA"]

   def bid_match(self, symbolic_bid: str) -> bool:
      if self.bid == symbolic_bid:
         return True
      if self.level != int(symbolic_bid[0]):
         return False
      return self.suit_code in SUIT_CODES_BY_GROUP[symbolic_bid[1:]]

 
def valid_symbolic_bid(value: str) -> bool:
   if value in [b.code for b in SpecialBid]:
      return True
   level = int(value[0]) if value[0].isdigit() else 0
   suit_code = value[1:] if level >= 1 else ""
   return level in range(1, 8) and suit_code in SYMBOLIC_SUIT_CODES


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


