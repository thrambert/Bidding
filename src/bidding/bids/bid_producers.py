from bids.bid_senses import BidSense
from bids.bids import Bid, Camp, Forcing
from bids.bid_records import BidRecord
from bids.hands import RichHand
from bids.hazes import Fit, Haze
from bids.slams import Slam


class BidProducer:
   """
   This class produces bidding without help of SEF rules. It is based on
   information gathered along previous bidding.

   Properties
   slam:          An instance to manage bids sequences in a slam perspective.
   haze:          Information on each player's hand deducted from bidding.
   rank:          Rank of the current player who has to make a bid
   camp:          Camp the player belongs to.
   partner_rank:  Rank of currentplayer's partner
   partner_bid:   Last bid made by partner.
   forcing:       Forcing indication in partner last bid.
   """
   def __init__(self):
      self.slam: Slam = None

   def _update_properties(self, record: BidRecord, haze: Haze):
      self.haze = haze
      self.rank = record.next_rank()
      self.camp = Camp.from_rank(self.rank)
      self.partner_rank = self.camp.other_rank(self.rank)
      self.partner_bid = Bid(self.record.second_last.raw)
      self.forcing = Forcing.from_value(self.record.second_last.sense.forcing)
   
   def make_bid(self, hand: RichHand, record: BidRecord, haze: Haze) -> BidSense:
      self._update_properties(record, haze)
      if self.forcing == Forcing.PASS:
         return BidSense.passe()
      fit = self.haze.fit(hand.cards_count, self.partner_rank)
      camp_points = self._compute_camp_points(hand, fit)
      if fit:
         return self._make_fitted_bid(hand, fit, camp_points)
      else:
         return self._make_unfitted_bid(camp_points)
      
   def _make_fitted_bid(self, hand: RichHand, fit: Fit, pts: int) -> BidSense:
      if pts >= 31 and not self.slam:
         self.slam = Slam(fit.suit, fit.total_cards, pts)
      if self.slam:
         declared_controls = self.haze.declared_controls(self.camp)
         return self.slam.next_bid(hand, self.partner_bid, declared_controls)
      elif (fit.major() and pts >= 26) or (fit.minor() and pts >= 28):
         next_raw_bid = ("4" if fit.major() else "5") + fit.suit.code
         return BidSense(id=0,raw_bid=next_raw_bid,forcing=Forcing.PASS.value)
      else:
         return BidSense.passe()
      
   def _make_unfitted_bid(self, pts: int) -> BidSense:
      if self.haze.stop_opp_suits(self.camp):
         return self._make_SA_bid(pts)
      else:
         return self._make_lowest_bid(self)
   
   def _make_SA_bid(self, pts: int) -> BidSense:
      if pts >= 32:
         return BidSense(id=0,raw_bid="6SA")
      elif pts >= 25:
         return BidSense(id=0,raw_bid="6SA")
      else:
         BidSense.passe()

   def _make_lowest_bid(self) -> BidSense:
      # TODO: Passe si les adv ont parlé, sinon chercher un fit 7e idéalement
      #  5-2, et l'annoncer ou passer si c'est la dernière enchère du partenaire.
      pass

   def _compute_camp_points(self, hand: RichHand, fit: Fit) -> int:
      if fit:
         return hand.points_HLD(fit.suit.code, fit.partner_count())
      else:
         return hand.points_HL + self.haze.hands[self.partner_rank].points.min
