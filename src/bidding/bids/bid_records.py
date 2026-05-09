from pydantic import computed_field
from bids.points import PointZone
from bids.bids import Bid, Camp
from bids.bid_rules import BidRule


PASS = "passe"


class Bidding(Bid):
   """
   This class stores a bid and position of player who made it, and the rule 
   from which bid has been deducted.
   
   Properties
   lap:        0 while everyone pass, then 1, then 2 after 4 bids, etc.
   rank:       1 to 4. Starts from dealer while everyone pass, then from opener.
   camp:       Camp of the player who made this bidding.
   rule:       Rule from which the bid has been deducted or None

   and properties of mother class.
   """
   def __init__(self, lap:int, rank: int, raw_bid: str, rule: BidRule = None):
      self.lap = lap
      self.rank = rank
      self.camp = Camp.from_rank(rank)
      self.rule = rule
      super().__init__(raw_bid)

   def in_intervention_camp(self) -> bool:
      return self.rank % 2 == 0
   

class BidRecord:
   """
   This class stores all bidding made during a game, and provides analysis on.
   
   Properties
   all:           All bidding made during the game until now.
   last:          Last bidding made or "".
   second_last:   "Avant-dernier" bidding made or "".
   """
   def __init__(self):
      self.all: list[Bidding] = []

   @computed_field
   @property
   def last(self) -> Bidding:
      if self.all:
         return self.all[-1]
   
   @computed_field
   @property
   def second_last(self) -> Bidding:
      if len(self.all) >= 2:
         return self.all[-2]

   def reversed_all(self) -> list[Bidding]:
      return self.all[::-1] if self.all else []
   
   def add_bidding(self, raw_bid: str, rule: BidRule) -> Bidding:
      lap, rank = self.get_next_lap_and_rank(raw_bid == PASS)
      new_bidding = Bidding(lap=lap, rank=rank, raw_bid=raw_bid, rule=rule)
      self.all.append(new_bidding)
      return new_bidding

   def partner_last_suit_code(self) -> str:
      if len(self.all) >= 2 and self.all[-2].suit_code:
         return self.all[-2].suit_code
      elif len(self.all) >= 6:
         return self.all[-6].suit_code
   
   def partner_splinter_code(self) -> str:
      if self.second_last.rule.convention == "Splinter":
         return self.second_last.raw

   def opponent_on_right_suit_code(self) -> str:
      if self.all:
         return self.last.suit_code

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
      bidding = [b for b in self.all if b.camp == Camp.INT and b.raw != PASS]
      return len(bidding)
   
   def get_declarer_rank(self) -> int:
      # Rank of the player who will play contract on given suit.
      for bidding in self.all:
         # TODO: openers_fit does not exist and should extend to not only opener camp
         if bidding.suit_code == self.openers_fit and bidding.rank in [1, 3]:
            self.openers_rank = bidding.rank

   def get_players_camp_points(self) -> dict:
      camp = Camp.from_rank(self.second_last.rank)
      players_pts = {camp.value[0]: (0, 40), camp.value[1]: (0, 40)}
      for bidding in [b for b in self.all if b.rank in camp.value and b.rule.points]:
         points = PointZone(bidding.rule.points)
         mini, maxi = players_pts[bidding.rank]
         players_pts[bidding.rank] = max(points.min, mini), min(points.max, maxi)
      return players_pts

   def get_next_lap_and_rank(self, next_bid_is_PASS: bool = False) -> tuple:
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
         if bidding.raw == PASS:
            count += 1
         else:
            break
      return count
