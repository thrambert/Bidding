from __future__ import annotations

from bids.hands import RichHand, MetaSuit
from bids.bids import Bid, Camp


class Slam:
   """
   This class concerns players of the same camp who envisage a slam (chelem).
   It calculates next bid to make by this camp, considering that opposit camp
   is passing.
   
   Properties
   camp:                Camp of players who are engaged in a slam process.
   fit:                 Fit on a suit between the 2 players of the camp.
   splinter_suit_code:  Suit code of the splinter if any.
   players_points:      Dict of min max HLD points, with player rank as dict key.
   ctrlled_suit_codes:  Suits codes the players declared control on except fit suit.
   """
   CONTROLS = [
      "3P",
      "4T",
      "4K",
      "4C",
      "4P",
   ]
   BLACKWOOD_BY_KEY = {
      0: "5T",
      1: "5K",
      2: "5C",
      3: "5T",
      4: "5K",
      12: "5P"
   }

   def __init__(self, fit: Fit, pts: dict, splinter: str = ""):
      self.camp = fit.camp
      self.fit = fit
      self.splinter_suit_code = splinter
      self.players_points: dict[int: tuple[int, int]] = pts
      self.ctrlled_suit_codes: set = {splinter} if splinter else {}

   def next_control(self, partner_last_bid: str, rank: int, hand: RichHand) -> str:
      """
      Returns next control, or 4SA, or 'la manche à la couleur' which is a stop.

      Arguments
      partner_last_bid: Partner last
      hand:             Hand of the player who has to make a bid.
      rank:             Rank of the player's partner.
      hand_ctrls:       Suit codes that player controls
      pts:              points HLD of player hand.
      """
      last_bid = Bid(partner_last_bid)
      hand_ctrls = hand.controlled_suits()
      controls_ok = self.ctrlled_suit_codes.union(hand_ctrls)
      if len(controls_ok) == 3 and self._little_slam_ok(rank, hand.points_HLD()):
         return self.BLACKWOOD["4SA"]
      for bid in [Bid(raw_bid) for raw_bid in self.CONTROLS]:
         if bid <= last_bid:
            # A control is skipped and missing --> stop to game (manche):
            if not bid.suit_code in controls_ok:
               return last_bid.first_bid_value_above_for(self.fit_suit_code)
         elif bid.suit_code in hand_ctrls and bid.suit_code != self.fit_suit_code:
            # Next control
            self.ctrlled_suit_codes.add(bid.suit_code)
            return bid.raw
      
   def next_blackwood(self, partner_last_bid: str, hand: RichHand, rank: int) -> str:
      # Returns next bid value in blackwood sequence
      if partner_last_bid == "4SA":
         return self._blackwood_answer(hand)
      elif partner_last_bid < "5SA":
         #TODO: complete function
         pass

   def _little_slam_ok(self, partner_rank: int, known_hand_pts: int) -> bool:
      # Returns True if camp points >= 33
      mini, _ = self.players_points[partner_rank]
      return mini + known_hand_pts >= 33
   
   def _blackwood_answer(self, hand: RichHand) -> str:
         nbr_keys, fit_queen = hand.blackwood_keys()
         magic_nbr = nbr_keys + (10 if fit_queen and nbr_keys == 2 else 0)
         return self.BLACKWOOD_BY_KEY[magic_nbr]


class Fit:
   """
   This class describes a fit in a suit that players of the same camp have
   identified.
   
   Properties
   camp:       Camp of players who are concerned by the fit.
   suit:       Suit for which these players are fitted.
   nbr_cards:  Nbr of fitted cards each player promised, ordered by player rank.
   """
   def __init__(self, camp: Camp, suit: str, players_nbr_cards: list):
      self.camp = camp
      self.suit = MetaSuit.from_code(suit)
      self.nbr_cards = players_nbr_cards
   
   def total_cards(self) -> int:
      return sum(self.nbr_cards.values())
   
   @staticmethod
   def get_best(fits: list[Fit]) -> Fit:
      if len(fits) == 1:
         return fits[0]
      fit1, fit2 = fits[0], fits[1]
      if fit1.suit.is_major() == fit2.suit.is_major():
         if fit1.total_cards() == fit2.total_cards():
            return fit1 if fit1._cards_gap() <= fit2._cards_gap() else fit2
         else:
            return fit1 if fit1.total_cards() > fit2.total_cards() else fit2
      else:
         return fit1 if fit1.suit.is_major() and fit1.total_cards() >= 8 else fit2

   def _cards_gap(self) -> int:
      return abs(self.nbr_cards[0] - self.nbr_cards[1])
