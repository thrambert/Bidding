"""
Removable.
This module is called by app.py to test bid_engines.
"""
from bridgebots.deal_enums import Direction
from deals.deal_engines import DealMaker, Vulnerability
from views.mats import BidChaining


# cards by suits spades,...,clubs for test deal:
TEST_HANDS = [
      "AKQ9876-K92-K9-A",
      "T-JT876-T7-KT984",
      "J54-A5-A865-Q765",
      "32-Q43-QJ432-J32",
]

def test_bidding():
   deal_maker = DealMaker(Direction.NORTH, Vulnerability.NONE)
   random_wanted = False
   if random_wanted:
      bid_chaining = BidChaining(deal_maker.create_random())
   else:
      bid_chaining = BidChaining(deal_maker.create_from_str(TEST_HANDS))

   bid_chaining.run_all()

