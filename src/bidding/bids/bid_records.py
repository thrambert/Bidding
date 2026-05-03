from functools import cached_property
from pydantic import BaseModel, computed_field
from typing import Union
from bids.bids import Forcing, SUIT_CODES_BY_GROUP


PASS = "passe"


class Bidding(BaseModel):
   """
   This class stores a bid and position of player who made it, and the rule 
   from which bid has been deducted.
   
   Properties
   lap:        0 while everyone pass, then 1, then 2 after 4 bids, etc.
   rank:       1 to 4. Starts from dealer while everyone pass, then from opener.
   bid:        Abbreviated bid in french. Examples: passe, 3SA, 1P
   rule_id:    id of the rule in file, or 0 if bid is passe
   artificial: True if bid is artificial, see Excel rules
   forcing:    A forcing enum or None, see Excel rules
   convention: The convention applied to define bid, see Excel rules.
   level:      Level of the bid. Example 3SA is level 3, PASSE is level 0.
   suit_code:  Bidding suit in 1 or 2 caps chr in french . Examples: C, SA.
   a_color:    True if bid on a color such as spade, heart, diamond or club.
   """
   lap: int
   rank: int
   bid: str
   rule_id: int = 0
   artificial: bool = False
   forcing: Union[Forcing, None] = None
   convention: str = ""

   
   @computed_field
   @cached_property
   def level(self) -> int:
      return int(self.bid[0]) if self.bid[0].isdigit() else 0
   
   @computed_field
   @cached_property
   def suit_code(self) -> str:
      if self.level >= 1:
         return self.bid[1:]

   @computed_field
   @cached_property
   def a_color(self) -> bool:
      return not self.suit_code in ["", "SA"]

   def in_intervention_camp(self) -> bool:
      return self.rank % 2 == 0
   
   def bid_match(self, symbolic_bid: str) -> bool:
      if self.bid == symbolic_bid:
         return True
      if self.level != int(symbolic_bid[0]):
         return False
      return self.suit_code in SUIT_CODES_BY_GROUP[symbolic_bid[1:]]


class BidRecord:
   """
   This class stores all bidding made during a game, and provides analysis on.
   
   Properties
   all:              All bidding made during the game until now.
   last:             Last bidding made.
   """
   def __init__(self):
      self.all: list[Bidding] = []

   @computed_field
   @property
   def last(self) -> Bidding:
      if self.all:
         return self.all[-1]
   
   def reversed_all(self) -> list[Bidding]:
      return self.all[::-1] if self.all else []
   
   def add_bidding(self, bid: str, rule_id: int = 0, artif: bool = False,
                   forcing: Forcing = None, conv: str = "") -> Bidding:
      lap, rank = self._get_next_lap_and_rank(bid == PASS)
      new_bidding = Bidding(
         lap=lap, rank=rank, bid=bid, rule_id=rule_id, artificial=artif,
         forcing=forcing, convention=conv
         )
      self.all.append(new_bidding)
      return new_bidding

   def partner_last_suit_code(self) -> str:
      if len(self.all) >= 2 and self.all[-2].suit_code:
         return self.all[-2].suit_code
      elif len(self.all) >= 6:
         return self.all[-6].suit_code
   
   def partner_made_splinter(self) -> bool:
      return self.all[-2].convention == "Splinter"

   def opponent_on_right_suit_code(self) -> str:
      if self.all:
         return self.all[-1].suit_code

   def opponent_on_left_suit_code(self) -> str:
      if len(self.all) >= 3:
         return self.all[-3].suit_code
      
   def opponents_suit_codes(self) -> list[str]:
      codes = [self.opponent_on_right_suit_code, self.opponent_on_left_suit_code]
      return [c for c in codes if c.strip()]

   def first_pass_count(self) -> int:
      return self._first_pass_count_in(self.all)

   def last_pass_count(self) -> int:
      return self._first_pass_count_in(self.reversed_all())
   
   def get_intervention_count(self) -> int:
      # Returns number of bids made by the intervention camp, pass excluding.
      bidding = [b for b in self.all if b.in_intervention_camp() and b.bid != PASS]
      return len(bidding)
   
   def get_declarer_rank(self) -> int:
      # Rank of the opener who will play contract on given suit.
      for bidding in self.all:
         # TODO: openers_fit does not exist and should extend to not only opener camp
         if bidding.suit_code == self.openers_fit and bidding.rank in [1, 3]:
            self.openers_rank = bidding.rank

   def _get_next_lap_and_rank(self, next_bid_is_PASS: bool) -> tuple:
      if self.all:
         last_bidding = self.last
         quotient, rest = divmod(last_bidding.rank, 4)
         return last_bidding.lap + quotient, 1 + rest
      else:
         return (0, 1) if next_bid_is_PASS else (1, 1)
      
   def _bidding_completed(self) -> bool:
      return len(self.all) >= 4 and self.last_pass_count() >= 3

   def _first_pass_count_in(self, bidding_list: list[Bidding]) -> int:
      count = 0
      for bidding in bidding_list:
         if bidding.bid == PASS:
            count += 1
         else:
            break
      return count
