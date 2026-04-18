"""
Removable.
This module is called by app.py to test bid_engines.
"""
from bridgebots.deal_enums import Direction
from engines.deal_engines import DealMaker, Vulnerability
from engines.bid_engines import BidMaker


# cards by suits spades,...,clubs for test deal:
TEST_HANDS = [
      "AKQ9876-K92-K9-A",
      "JT-AJT87-T7-KT98",
      "54-65-A865-Q7654",
      "32-Q43-QJ432-J32",
]

def test_bidding():
   deal_maker = DealMaker(Direction.NORTH, Vulnerability.NONE)
   random_wanted = False
   if random_wanted:
      bid_maker = BidMaker(deal_maker.create_random())
   else:
      bid_maker = BidMaker(deal_maker.create_from_str(TEST_HANDS))

   bid_maker.run_all()

