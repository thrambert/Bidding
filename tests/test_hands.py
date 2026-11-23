import unittest

from bidding.bids.hands import MetaSuit
from tests.helpers import make_hand


class TestDefTricks(unittest.TestCase):
    # 1c: pattern 'AR' never matched, the king's abbreviation being 'K'.
    def test_ace_king_counts_two_tricks(self):
        self.assertEqual(make_hand("AK32-A54-K432-32").def_tricks, 3)

    def test_ace_king_in_long_suit_counts_one_trick(self):
        self.assertEqual(make_hand("AK5432-A5-432-32").def_tricks, 2)


class TestRankComparisons(unittest.TestCase):
    # 1d: ranks were compared to strings ('KING', 'ACE'...).
    def test_king_second(self):
        hand = make_hand("AK32-K5-QJ32-432")
        self.assertTrue(hand.king_second(MetaSuit.HEARTS))
        self.assertFalse(hand.king_second(MetaSuit.SPADES))

    def test_covering_count(self):
        # Bicolor: spades AKQ (3) + hearts K (1); others: diamond A (1) + club KQ (1).
        hand = make_hand("AKQ32-K5432-A-KQ")
        self.assertEqual(hand.covering_count([MetaSuit.SPADES, MetaSuit.HEARTS]), 6)


class TestWonTricksHonors(unittest.TestCase):
    # 1e: only pattern 'AKQ' was tested, any other returned 0.
    def test_patterns_beyond_first_one(self):
        hand = make_hand("AK32-A54-K432-32")
        cases = {"AKQ2": 3, "AK": 2, "A5": 1, "KQ3": 1.25, "K4": 0.5, "Q32": 0.25, "J5": 0, "": 0}
        for cards, expected in cases.items():
            self.assertEqual(hand._won_tricks_honors(cards), expected, cards)

    def test_won_tricks_includes_honors(self):
        # Length: 0.5 (spades) + 0.5 (diamonds); honors: AK 2 + A 1 + K. 0.5
        self.assertEqual(make_hand("AK32-A54-K432-32").won_tricks, 4.5)


class TestOneMajorAce(unittest.TestCase):
    # 1f: aces_count was not called, so the result was always False.
    def test_single_major_ace(self):
        self.assertTrue(make_hand("A5432-K5432-K2-2").has_one_major_ace_and_no_minor())

    def test_minor_ace_too(self):
        self.assertFalse(make_hand("A5432-K5432-A2-2").has_one_major_ace_and_no_minor())

    def test_two_major_aces(self):
        self.assertFalse(make_hand("A5432-A5432-32-2").has_one_major_ace_and_no_minor())


if __name__ == "__main__":
    unittest.main()
