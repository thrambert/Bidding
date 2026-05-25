from pydantic import computed_field
from bids.points import PointZone
from bids.bids import Bid, Camp
from bids.bid_senses import BidSense


PASS = "passe"


class Bidding(Bid):
   """
   This class stores a bid and position of player who made it, and the sense 
   which gives information deducted from bid.
   
   Properties
   lap:        0 while everyone pass, then 1, then 2 after 4 bids, etc.
   rank:       1 to 4. Starts from dealer while everyone pass, then from opener.
   camp:       Camp of the player who made this bidding.
   sense:      Sense of the bid made (Information deducted from bid), or None.

   Other properties: See mother class.
   """
   def __init__(self, lap: int, rank: int, sense: BidSense):
      self.lap = lap
      self.rank = rank
      self.camp = Camp.from_rank(rank)
      self.sense = sense
      super().__init__(sense.raw_bid)

   def is_natural_suit(self) -> bool:
      # Returns True if bid is on a real suit (not SA) and is natural bid.
      return self.a_color and not self.sense.artificial


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
   
   def add_bidding(self, bid_sense: BidSense):
      lap = self.next_lap(bid_sense.raw_bid == PASS)
      rank = self.next_rank()
      new_bidding = Bidding(lap, rank, bid_sense)
      self.all.append(new_bidding)
   
   def last_normal_bid(self) -> Bidding:
      if not self.all:
         return None
      for bidding in self.reversed_all():
         if not bidding.a_special:
            return bidding

   def partner_last_suit_code(self) -> str:
      if len(self.all) >= 2 and self.all[-2].suit_code:
         return self.all[-2].suit_code
      elif len(self.all) >= 6:
         return self.all[-6].suit_code
   
   def partner_splinter_code(self) -> str:
      if self.second_last.sense.convention == "Splinter":
         return self.second_last.raw

   def opponent_on_right_suit_code(self) -> str:
      # Returns suit code of opponent on the right if his bid is natural.
      if self.all:
         return self.last.suit_code

   def opponent_on_left_suit_code(self) -> str:
      # Returns suit code of opponent on the left if his bid is natural.
      if len(self.all) >= 3:
         return self.all[-3].suit_code
   
   def opponents_suit_codes(self) -> list[str]:
      # Returns codes of all suits naturally announced by the opponents
      opp_camp = self.last.camp
      opp_biddings = [b for b in self.all if b.camp == opp_camp]
      return [b.suit_code for b in opp_biddings if b.is_natural_suit()]

   def first_pass_count(self) -> int:
      return self._first_pass_count_in(self.all)

   def sleep(self) -> bool:
      last_pass_count = self._first_pass_count_in(self.reversed_all())
      return last_pass_count == 2
   
   def nbr_interventions(self) -> int:
      # Returns number of bids made by the intervention camp, pass excluded.
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
      for bidding in [b for b in self.all if b.rank in camp.value and b.sense.points]:
         points = PointZone(bidding.sense.points)
         mini, maxi = players_pts[bidding.rank]
         players_pts[bidding.rank] = max(points.min, mini), min(points.max, maxi)
      return players_pts

   def next_lap(self, next_bid_is_PASS: bool) -> int:
      if self.last:
         return self.last.lap + self.last.rank // 4
      else:
         return 0 if next_bid_is_PASS else 1
   
   def next_rank(self) -> int:
      return self.last.rank % 4 + 1 if self.last else 1

   def _first_pass_count_in(self, bidding_list: list[Bidding]) -> int:
      count = 0
      for bidding in bidding_list:
         if bidding.raw == PASS:
            count += 1
         else:
            break
      return count
