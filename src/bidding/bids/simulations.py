"""
Removable.
This module is called by app.py to run bid_engines on generated deals.
"""

from datetime import datetime

from bridgebots.deal_enums import Direction

from bidding.bids.bid_histories import BidHistory
from bidding.bids.bid_rules import BidRule
from bidding.deals.deal_engines import DealMaker, Vulnerability
from bidding.views.mats import BidChaining

# cards by suits spades,...,clubs for test deal:
TEST_HANDS = []


def run_simulations():
    """List all sequences into dna.csv"""

    # dna = Dna(sort_by_length=False)
    # dna.write_in_file()

    # Test bidding while generating deals

    if TEST_HANDS:
        simulate_one_deal()
    else:
        simulate_several_deals(5000)


def simulate_one_deal():
    deal_maker = DealMaker(Direction.NORTH, Vulnerability.NONE)
    deal = deal_maker.create_from_str(TEST_HANDS)
    bid_chaining = BidChaining(deal)
    bid_chaining.run(debug=True)


def simulate_several_deals(count: int):
    deal_maker = DealMaker(Direction.NORTH, Vulnerability.NONE)
    start_time = datetime.now()
    for i in range(1, count + 1):
        deal = deal_maker.create_random()
        bid_chaining = BidChaining(deal)
        bid_chaining.run(debug=True)
        if i == 1:
            print(f"          {i:>4} bid")
        elif i % 200 == 0:
            delay = datetime.now() - start_time
            delay_for_1000 = delay.seconds * 1000 / i
            print(
                f"          {i:>4} bids, average time for one bid (millisec): {delay_for_1000:.2f}"
            )
        if i == count:
            print()

    write_summary(rules_ids=BidHistory.get_all_rules_ids())


def write_summary(rules_ids: list[int]):
    size = 20
    intervals = []
    previous_id = 0
    for id in rules_ids:
        if id > previous_id + size:
            intervals.append(f"{str(previous_id + 1)} - {str(id - 1)}, ")
        previous_id = id
    if BidRule.get_last_id() > previous_id + size:
        intervals.append(f"{str(previous_id + 1)} - {BidRule.get_last_id()}")

    print(f"--> {len(rules_ids)} satisfied rules: {rules_ids}")
    print()
    print(f"--> {len(intervals)} intervals >= {size} of non applied rules:")
    for interval in intervals:
        print(f"      {interval}")


#  Distribution très intéressante vue le 16-07-2026,
#  pour approfondir BidProducer et résoudre des bugs:
# TEST_HANDS = ['Q65432-Q-T7432-8', '87-AK-AKQJ9865-Q', 'AKJT9-T983--T965', '-J76542--AKJ7432']

#  Unicolor
# TEST_HANDS = [
#    "AKQ987-A92-K9-A4",
#    "T6-JT876-T7-QT98",
#    "J54-K5-A865-K765",
#    "32-Q43-QJ432-J32",
# ]

# Unicolor
# TEST_HANDS = [
#    "AKQ9876-K92-K9-A",
#    "T-JT876-T7-KT984",
#    "J54-A5-A865-Q765",
#    "32-Q43-QJ432-J32",
# ]

# Slam 6S
# TEST_HANDS = [
#    "AKQ9-T92-K9-AJT4",
#    "86-J876-T75-Q982",
#    "JT54-AKQ-A86-K76",
#    "732-543-QJ432-53",
# ]

# Bicolore cher
# TEST_HANDS = [
#    "AKQ9-Q9-KQJ98-A4",
#    "6-J8763-T75-Q982",
#    "J854-A2-A6-KJ653",
#    "T732-KT54-432-T7",
# ]

# Intervention bicolore Michael cuebid
# TEST_HANDS = [
#    "AKQ98-Q9-T987-J4",
#    "6-AKJ87-65-AKQ98",
#    "J54-2-AK432-6532",
#    "T732-T6543-QJ-T7",
# ]

# Intervention bicolore Michael cuebid suivie d'une défense par joueur N°3 à 3SA
# TEST_HANDS = [
#    "AKQ98-Q9-J987-64",
#    "6-KJ872-65-AKJ98",
#    "J54-A3-AK432-Q53",
#    "T732-T654-QT-T72",
# ]

# Contre d'appel et réponse au contre d'appel avec un double saut au palier de 3
# TEST_HANDS = [
#    "J56-AKQ23-Q23-78",
#    "AKQ9-T9-AJ45-Q32",
#    "4-45-K6789-456T9",
#    "T2378-J876-T-AKJ",
#    ]
