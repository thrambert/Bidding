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
   count:         Number of recorded bids.
   last:          Last bidding made or "".
   second_last:   "Avant-dernier" bidding made or "".
   third_last     "Avant-avant-dernier" bidding or "".
   """
   def __init__(self):
      self.all: list[Bidding] = []

   @computed_field
   @property
   def count(self) -> int:
      return len(self.all)
   
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

   @computed_field
   @property
   def third_last(self) -> Bidding:
      if len(self.all) >= 3:
         return self.all[-3]

   def reversed_all(self) -> list[Bidding]:
      return self.all[::-1] if self.all else []
   
   def add_bidding(self, bid_sense: BidSense):
      lap, rank = self.next_lap_and_rank(bid_sense.raw_bid == PASS)
      new_bidding = Bidding(lap, rank, bid_sense)
      self.all.append(new_bidding)
   
   def last_normal_bid(self) -> Bidding:
      if not self.all:
         return None
      for bidding in self.reversed_all():
         if not bidding.a_special:
            return bidding

   def suit_codes(self, camp: Camp) -> list[str]:
      # Returns codes of all suits naturally announced by given camp,
      #  without duplicate values and sorted from the oldest to the most recent.
      suit_codes = []
      for bid in self.all:
         if bid.camp == camp and bid.is_natural_suit():
            if not bid.suit_code in suit_codes:
               suit_codes.append(bid.suit_code)
      return suit_codes

   def last_suit_code(self, camp: Camp) -> str:
      suit_codes = self.suit_codes(camp)
      return suit_codes[-1] if suit_codes else ""

   def first_pass_count(self) -> int:
      return self._first_pass_count_in(self.all)

   def sleep(self) -> bool:
      last_pass_count = self._first_pass_count_in(self.reversed_all())
      return last_pass_count == 2
   
   def nbr_interventions(self) -> int:
      # Returns number of bids made by the intervention camp, pass excluded.
      bidding = [b for b in self.all if b.camp == Camp.INT and b.raw != PASS]
      return len(bidding)
   
   def get_players_camp_points(self) -> dict:
      camp = Camp.from_rank(self.second_last.rank)
      players_pts = {camp.value[0]: (0, 40), camp.value[1]: (0, 40)}
      for bidding in [b for b in self.all if b.rank in camp.value and b.sense.points]:
         points = PointZone(bidding.sense.points)
         mini, maxi = players_pts[bidding.rank]
         players_pts[bidding.rank] = max(points.min, mini), min(points.max, maxi)
      return players_pts

   def next_lap_and_rank(self, next_bid_is_PASS: bool) -> tuple[int, int]:
      if not self.last:
         lap = 0 if next_bid_is_PASS else 1
         return lap, 1
      if self.last.lap == 0 and not next_bid_is_PASS:
         return 1, 1
      else:
         quotient, remainder = divmod(self.last.rank, 4)
         lap = self.last.lap + quotient
         rank = remainder + 1
         return lap, rank

   def no_open(self) -> bool:
      if self.last:
         return self.last.lap == 0
      else:
         return True
   
   def comply_with(self, requested_bids: list[Bid]) -> bool:
      """
      Returns True if requested bids match with recorded bids. 
      In requested bids, symbolic suits are managed as below :
       - if M appears several times, it represents same suit each time, and
         same for m and E.
       - E represents a suit which must not be already present in history,
         nor a suit represented by M or m.
      """
      if len(self.all) < len(requested_bids):
         return False
      hist_bidding = self.reversed_all()
      convert = {"M": "", "m": "", "E": ""}
      real_suit_codes = set()
          
      for i, bid in enumerate(requested_bids):
         if not hist_bidding[i].bid_match(bid):
            return False
         symbol_E = (bid.suit_code == "E")
         if bid.a_symbol:
            if not convert[bid.suit_code]:
               convert[bid.suit_code] = hist_bidding[i].suit_code
            bid = bid.replace_suit_with(convert[bid.suit_code])
         if not symbol_E:
            real_suit_codes.add(bid.suit_code)

      return not (convert["E"] and convert["E"] in real_suit_codes)

   def _first_pass_count_in(self, bidding_list: list[Bidding]) -> int:
      count = 0
      for bidding in bidding_list:
         if bidding.raw == PASS:
            count += 1
         else:
            break
      return count
