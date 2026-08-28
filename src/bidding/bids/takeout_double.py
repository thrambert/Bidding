from bids.hands import MetaSuit
from bids.bids import Bid


class TakeoutDouble:
   """
   This class manages a takeout double (Contre d'appel in French).
   It provides functions related to takeout double and its developments,
   examining hand of the player who has to make a bid.
   
   Properties
   length:           In player's hand, number of cards per suit unnamed by opp,
                     sorted by decreased length.
   sorted_suits      Suits unnamed by opp, sorted by decreased length, and then
                     from spade to club.
   """
   def __init__(self, cards_count: dict[MetaSuit: int], opp_suit_codes: set):
      """
      Arg
      cards_count:   Number of cards per suit of player's hand, in decreased order.
      opp_suit_codes: Codes of suits naturally announced by opponent camp.
      """
      self.length: dict[MetaSuit: int] = {s: n for s, n in cards_count.items() \
                                          if s.code not in opp_suit_codes}
      suits = sorted(self.length.keys(), reverse=True)
      self.sorted_suits = sorted(suits, key=lambda s: cards_count[s], reverse=True)

   def allowed(self) -> bool:
      # Returns True if distribution is ok for a takeout double
      if self.length[self.sorted_suits[-1]] < 3:
         return False
      major_length = [nbr for s, nbr in self.length.items() if s.is_major()]
      if len(major_length) == 2:
         return sum(major_length) >= 7
      elif len(major_length) == 1:
         return sum(major_length) >= 4
      else:
         return True

   def answer(self, last_normal_bid: Bid, jump: bool) -> str:
      # Returns raw bid to answer to a takeout double.
      bid = last_normal_bid.first_bid_above(for_suit=self.sorted_suits[0])
      if jump:
         return str(self._level_after_jump(bid.suit, bid.level)) + bid.suit_code
      else:
         return bid.raw

   def _level_after_jump(self, suit: MetaSuit, base_level: int) -> int:
      """
      Returns level to apply to when jumping to answer takeout double :
       - single jump for a major with 4 cards until level 3
       - double jump for a major with 5 cards until level 3
       - triple jump for a major with 6 cards until level 4
       - jump at level 3 for a minor with 5 cards
      """
      if suit.is_major():
         jump, max_level = self.length[suit] -3, 3 if self.length[suit] <= 5 else 4
         return min(base_level + jump, max_level)
      elif self.length[suit] == 5:
         return min(base_level + 1, 3)
      else:
         return base_level

   