from __future__ import annotations

from functools import cached_property
from pydantic import BaseModel, computed_field
from bids.hands import Distribution, MetaSuit
from bids.bids import Camp, Bid
from bids.bid_senses import BidSense
from bids.points import PointZone


class Fit(BaseModel):
   """
   This class describes a fit in a suit that players of the same camp have
   identified.
   
   Properties
   suit:       Suit for which these players are fitted.
   counts:     Min number of cards in suit for players of same camp: [n, p],
               where n is for player and p for his partner.
   """
   suit: MetaSuit
   counts: list[int]
   
   @computed_field
   @cached_property
   def total_cards(self) -> int:
      return sum(self.counts)
   
   def major(self) -> bool:
      return self.suit.is_major()
   
   def minor(self) -> bool:
      return self.suit.is_minor()
         
   def partner_count(self) -> int:
      return self.counts[0]
   
   def _cards_gap(self) -> int:
      return abs(self.counts[0] - self.counts[1])
   
   @staticmethod
   def get_best(fits: list[Fit]) -> Fit:
      if not fits:
         return None
      elif len(fits) == 1:
         return fits[0]
      fit1, fit2 = fits[0], fits[1]
      if fit1.suit.is_major() == fit2.suit.is_major():
         if fit1.total_cards == fit2.total_cards:
            return fit1 if fit1._cards_gap() <= fit2._cards_gap() else fit2
         else:
            return fit1 if fit1.total_cards > fit2.total_cards else fit2
      else:
         return fit1 if fit1.suit.is_major() and fit1.total_cards >= 8 else fit2


class HazySuit(BaseModel):
   """
   This class stores information on a suit inside a player hand deducted from
   bidding.

   Properties
   min_nbr:       Minimum number of cards declared by player through bidding.
   max_nbr:       Maximum number of cards declared.
   announced:     True if this suit has been naturally announced by player.
   stop:          True if at least one stop declared by player for this suit.
   control:       True if a control on the suit has been declared by player.
   force:         True if a force in the suit has been declared by player.
   """
   min_nbr: int = 0
   max_nbr: int = 13
   announced: bool = False
   stop: bool = False
   control: bool = False
   force: bool = False
   
   def set_length(self, expr: str):
      is_min, value = self._get_min_max(expr)
      if is_min:
         self.min_nbr = max(self.min_nbr, value)
      else:
         self.max_nbr = min(self.max_nbr, value)
      
   def set_bools(self, bools: dict):
      self.stop = self.stop or bools["stop"]
      self.control = self.control or bools["control"]
      self.force = self.force or bools["force"]

   def _get_min_max(self, expr: str) -> tuple[bool, int]:
      # Returns (is_min, value) where value is inclusive and is_min is True if
      #  value is a minimum else it is a maximum. expr: n, <n, <=n, >n or >=n.
      if expr[0].isdigit():
         return int(expr), int(expr)
      inclusive = (expr[1] == "=")
      compact_expr = expr.replace("=", "")
      greater_than = (compact_expr[0] == ">")
      value = int(compact_expr[1:]) + (0 if inclusive else 2 * greater_than - 1)
      return greater_than, value


class HazyHand:
   """
   This class stores information on a player hand deducted from bidding.
   
   Properties
   rank:          Rank of the player in bidding from 1 to 4. 1 is the opener.
   camp:          Camp the player belongs to.
   distribution:  French distrib the hand matches with.
   h_suits:       Dict of the four hazy suits.
   """
   def __init__(self, rank: int):
      self.rank = rank
      self.camp = Camp.from_rank(rank)
      self.points = PointZone()
      self.distribution: Distribution = None
      self.h_suits = {suit: HazySuit() for suit in MetaSuit.four_suits()}

   def store(self, sense: BidSense, bid: Bid, par_bid: Bid, opp_suits_c: list[str]):
      self._set_suits_length(sense.four_suits_count())
      if sense.points:
         self.points = PointZone(sense.points)
      if sense.distribution:
         self.distribution = Distribution(sense.distribution)
         self._apply_distribution()
      if sense.par_suit_count:
         self.h_suits[par_bid.suit].set_length(sense.par_suit_count)
      if sense.suit_count:
         self._set_suit_count(bid, sense.suit, sense.suit_count)
      if sense.opp_stop:
         self._set_stopped_opp_suits(opp_suits_c)
      if bid.a_color:
         self.h_suits[bid.suit].set_bools(sense.player_suit_type())
      if bid.a_color and not sense.artificial:
         self.h_suits[bid.suit].announced = True

   def min_lengths(self) -> dict[MetaSuit, int]:
      return {suit: h_suit.min_nbr for suit, h_suit in self.h_suits.items()}

   def _apply_distribution(self):
      if self.distribution.semi_regular():
         for suit in MetaSuit.four_suits():
            self.h_suits[suit].set_length(">=2")
   
   def _set_suits_length(self, suits_count: list[str]):
      # arg 'suits_count' gives count expr for suits from club to spade.
      for suit_rank, count_expr in enumerate(suits_count):
         if count_expr:
            suit = MetaSuit.from_rank(suit_rank)
            self.h_suits[suit].set_length(count_expr)

   def _set_suit_count(self, bid: Bid, sense_suit: str, sense_suit_count: str):
      suit = MetaSuit.from_text(sense_suit) if sense_suit else bid.suit
      self.h_suits[suit].set_length(sense_suit_count)

   def _set_stopped_opp_suits(self, opp_suits_codes: list[str]):
      for suit in [MetaSuit.from_code(c) for c in opp_suits_codes]:
         self.h_suits[suit].stop = True


class Haze:
   """
   This class gather information on each player's hand deducted from bidding.

   Properties
   hands:         dict {rank: HazyHand}
   """
   def __init__(self):
      self.hands = {rank: HazyHand(rank) for rank in range(1, 5)}

   def store(self, sense: BidSense, rank: int, par_bid: Bid, opp_suits_c: list[str]):
      bid = Bid(sense.raw_bid)
      self.hands[rank].store(sense, bid, par_bid, opp_suits_c)

   def fit(self, player_cards_count: dict[MetaSuit, int], partner_rank: int) -> Fit:
      # Returns suit code and nbr of cards in it if fitted else None
      partner_card_counts = self.hands[partner_rank].min_lengths()
      possible_fits = []
      for suit in MetaSuit.four_suits():
         card_counts = [player_cards_count[suit], partner_card_counts[suit]]
         if sum(card_counts) >= 8:
            possible_fits.append(Fit(suit=suit, counts=card_counts))
      return Fit.get_best(possible_fits)

   def declared_controls(self, camp: Camp) -> set[str]:
      h_suits = self._merged_suits(camp)
      ctrls = [s.code for s in MetaSuit.four_suits() if h_suits[s].control]
      return set(ctrls)

   def stop_opp_suits(self, camp: Camp) -> bool:
      camp_h_suits = self._merged_suits(camp)
      opp_camp = camp.other_camp()
      opp_h_suits = self._merged_suits(opp_camp)
      opp_suits = [s for s, value in opp_h_suits.items() if value.announced]
      no_stops = [1 for s in opp_suits if not camp_h_suits[s].stop]
      return len(no_stops) == 0

   def _merged_suits(self, camp: Camp) -> dict[MetaSuit, HazySuit]:
      a, b = camp.value
      a_suits, b_suits = self.hands[a].h_suits, self.hands[b].h_suits
      merged = {suit: HazySuit() for suit in MetaSuit.four_suits()}
      for s in MetaSuit.four_suits():
         merged[s].min_nbr = a_suits[s].min_nbr + b_suits[s].min_nbr
         merged[s].max_nbr = a_suits[s].max_nbr + b_suits[s].max_nbr
         merged[s].announced = a_suits[s].announced or b_suits[s].announced
         merged[s].stop = a_suits[s].stop or b_suits[s].stop
         merged[s].control = a_suits[s].control or b_suits[s].control
         merged[s].force = a_suits[s].force or b_suits[s].force
      return merged