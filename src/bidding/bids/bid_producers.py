from bids.bid_senses import BidSense
from bids.bids import Bid, Camp, Forcing
from bids.bid_records import BidRecord
from bids.hands import MetaSuit, RichHand
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
   partner_rank:  Rank of current player's partner
   partner_raw_bid:   Last raw bid made by partner.
   forcing:       Forcing indication in partner last bid.
   """
   def __init__(self, haze: Haze):
      self.haze = haze
      self.slam: Slam = None

   def _update_properties(self, record: BidRecord):
      _, self.rank = record.next_lap_and_rank(False)
      self.camp = Camp.from_rank(self.rank)
      self.partner_rank = self.camp.other_rank(self.rank)
      self.partner_raw_bid = record.second_last.raw
      self.last_normal_bid = record.last_normal_bid()
      self.forcing = Forcing.from_value(record.second_last.sense.forcing)
   
   def make_bid(self, hand: RichHand, record: BidRecord) -> BidSense:
      # TODO Manage additional cases :
      #      - when opponents talk or take double
      #      - after 2 passes (en réveil)
      self._update_properties(record)
      if self.forcing == Forcing.PASS:
         return BidSense.passe()
      fit = self.haze.fit(hand.cards_count, self.partner_rank)
      camp_points = self._compute_camp_points(hand, fit)
      return self._steer_bid_to_make(hand, fit, camp_points)
      
   def _steer_bid_to_make(self, hand: RichHand, fit: Fit, pts: int) -> BidSense:
      if fit:
         return self._steer_fitted(hand, fit, pts)
      else:
         return self._make_unfitted_bid(self.last_normal_bid, pts)
         
   def _steer_fitted(self, hand: RichHand, fit: Fit, pts: int) -> BidSense:
      minor_ctr = fit.minor() and (pts >= 31 or Bid("3SA") < self.last_normal_bid)
      if fit.major() or minor_ctr:
         return self._make_fitted_bid(hand, fit, pts)
      else:
         #TODO SA if we stop opp suits, or announce a force,
         #  or 4e suit forcing, or play with 5-2 fit or pass.
         #  En attendant on génère un bid pass (à supprimer par la suite):
         return BidSense.passe()

   def _make_fitted_bid(self, hand: RichHand, fit: Fit, pts: int) -> BidSense:
      if pts >= 31 and not self.slam:
         self.slam = Slam(fit.suit, fit.total_cards, pts)
         self.haze.set_implicit_fit(fit.suit, self.camp, self.partner_rank)
      if self.slam:
         declared_controls = self.haze.declared_controls(self.camp)
         return self.slam.next_bid(hand, self.partner_raw_bid, declared_controls)
      elif (fit.major() and pts >= 26) or (fit.minor() and pts >= 28):
         next_raw_bid = ("4" if fit.major() else "5") + fit.suit.code
         return BidSense(id=0,raw_bid=next_raw_bid,forcing=Forcing.PASS.value)
      else:
         next_raw_bid = self.last_normal_bid.first_bid_above_or_pass(fit.suit).raw
         return BidSense(id=0,raw_bid=next_raw_bid)
      
   def _make_unfitted_bid(self, last_normal_bid: Bid, pts: int) -> BidSense:
      if self.haze.stop_opp_suits(self.camp):
         return self._make_SA_bid(last_normal_bid, pts)
      else:
         return self._make_lowest_bid()
   
   def _make_SA_bid(self, last_normal_bid: Bid, pts: int) -> BidSense:
      Bid_3SA = Bid("3SA")
      Bid_6SA = Bid("6SA")
      if pts >= 32 and last_normal_bid < Bid_6SA:
         return BidSense(id=0,raw_bid=Bid_6SA.raw)
      elif pts >= 25 and last_normal_bid < Bid_3SA:
         return BidSense(id=0,raw_bid=Bid_3SA.raw)
      else:
         return BidSense.passe()

   def _make_lowest_bid(self) -> BidSense:
      # TODO: Passe si les adv ont parlé, sinon chercher un fit 7e idéalement
      #  5-2, et l'annoncer ou passer si c'est la dernière enchère du partenaire.
      #  En attendant on génère un bid pass (à supprimer par la suite):
      return BidSense.passe()

   def _compute_camp_points(self, hand: RichHand, fit: Fit) -> int:
      if fit:
         player_points = hand.points_HLD(fit.suit, fit.partner_count())
      else:
         player_points = hand.points_HL
      return player_points + self.haze.hands[self.partner_rank].points.min
