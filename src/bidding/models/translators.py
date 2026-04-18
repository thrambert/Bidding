"""
This module translates data from english to french and vice versa.
"""

# =============================================================================
#  DICTIONARIES
# =============================================================================

_SUIT_SHORT = {
   "S": "P",      # spade -   pique
   "H": "C",      # heart -   coeur
   "D": "K",      # diamond - carreau
   "C": "T",      # club -    trèfle
}

_SUIT = {
   "S": "pique",
   "H": "coeur",
   "D": "carreau",
   "C": "trèfle",
}

_SPECIAL_BID_SHORT = {
   "NT": "SA",    # no trump - sans atout
   "PASS": "PASSE",
   "X": "X",
   "XX": "XX",
}

_SPECIAL_BID = {
   "NT": "sans atout",
   "PASS": "passe",
   "X": "contre",
   "XX": "surcontre",
}

_BID_SHORT = _SUIT_SHORT | _SPECIAL_BID_SHORT
_BID = _SUIT | _SPECIAL_BID


# =============================================================================
#  FUNCTIONS
# =============================================================================


class FrenchToEnglish:
   # This class is abstract to provide translate functions.

   def bid_short(self, bid_fr: str) -> str:
      # Returns a 1 letter suit or compact special bid
      dic = self._revert(_BID_SHORT)
      return dic[bid_fr]
   
   def suit(self, suit_fr: str) -> str:
      # Returns a 1 letter suit. Given arg is suit word in french minsucule.
      dic = self._revert(_SUIT)
      return dic[suit_fr]

   def _revert(self, origin_dict: dict) -> dict:
      return {value: key for key, value in origin_dict.items()}

