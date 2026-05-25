"""
Removable.
This module is called by app.py to test bid_engines.
"""
from bridgebots.deal_enums import Direction
from deals.deal_engines import DealMaker, Vulnerability
from views.mats import BidChaining


# cards by suits spades,...,clubs for test deal:
TEST_HANDS = [
   "AKQ9-T92-K9-AJT4",
   "86-J876-T75-Q982",
   "JT54-AKQ-A86-K76",
   "732-543-QJ432-53",
]

def test_bidding():
   deal_maker = DealMaker(Direction.NORTH, Vulnerability.NONE)
   random_wanted = False
   if random_wanted:
      bid_chaining = BidChaining(deal_maker.create_random())
   else:
      bid_chaining = BidChaining(deal_maker.create_from_str(TEST_HANDS))

   bid_chaining.run_all()

#  Unicolor
# TEST_HANDS = [
#    "AKQ987-A92-K9-A4",
#    "T6-JT876-T7-QT98",
#    "J54-K5-A865-K765",
#    "32-Q43-QJ432-J32",
# ]

# Unicolor
# TEST_HANDS = [
#       "AKQ9876-K92-K9-A",
#       "T-JT876-T7-KT984",
#       "J54-A5-A865-Q765",
#       "32-Q43-QJ432-J32",
# ]
