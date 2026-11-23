import unittest
from unittest.mock import patch

from bidding.bids.bid_engines import BidComputer, BidEngine, RuleAnalyzer
from bidding.bids.bid_rules import BidRule
from bidding.bids.bid_senses import BidSense
from bidding.utils import MyDataException
from tests.helpers import make_hand, make_record

# 4 spades, 3 hearts, 14 H points: best major is spades.
HAND = "AK32-A54-K432-32"


def make_rule(**fields) -> BidRule:
    return BidRule(id=1, step="OPEN", opp_next_step="", camp_next_step="", **fields)


# Partner (rank 1) opened 1C, opponent passed: current player has rank 3.
OPENED_1C = ("1C", "passe")


def analyzer(spec: str, *raw_bids: str) -> RuleAnalyzer:
    return RuleAnalyzer(make_hand(spec), 0, make_record(*raw_bids), None)


class TestOpMatch(unittest.TestCase):
    # 2.1: eval() replaced by an operator table.
    def setUp(self):
        self.analyzer = RuleAnalyzer(None, 0, None, None)

    def test_operators(self):
        cases = [
            ("4", 4, True),
            ("4", 3, False),
            ("=0", 0, True),
            ("==2", 2, True),
            ("<4", 3, True),
            ("<4", 4, False),
            ("<=1", 1, True),
            (">3", 3, False),
            (">=2", 2, True),
            (">=1.5", 1.5, True),
            (">=1,5", 1, False),
        ]
        for inequality, value, expected in cases:
            self.assertIs(self.analyzer.op_match(inequality, value), expected, (inequality, value))

    def test_invalid_inequality_raises(self):
        for inequality in ["", ">=", "a5", "5>", "==__import__('os')"]:
            with self.assertRaises(MyDataException, msg=inequality):
                self.analyzer.op_match(inequality, 1)


class TestHandChecks(unittest.TestCase):
    def test_ace_check(self):
        # 1d: first rank was compared to "ACE".
        self.assertTrue(analyzer("A5432-K5432-K2-2")._ace_check("P3"))
        self.assertFalse(analyzer("A5432-K5432-K2-2")._ace_check("K1"))

    def test_no_good_major_5(self):
        # 1h: is_major was not called, so minor suits were treated as majors.
        self.assertFalse(analyzer("AQ432-32-5432-32")._no_good_major_5_check())
        self.assertTrue(analyzer("32-32-AKQ43-5432")._no_good_major_5_check())

    def test_any_short_color(self):
        # 1k: the longest suit was tested instead of the shortest one.
        self.assertTrue(analyzer("A5432-K5432-K2-2")._any_short_color_check())
        self.assertFalse(analyzer("A432-K32-Q32-432")._any_short_color_check())

    def test_stop_suit_accepts_decimal(self):
        # 1k: int("1.5") raised ValueError. Clubs KQ3 = 1.5 stop.
        self.assertTrue(analyzer("5432-5432-32-KQ3")._stop_suit_check("T1.5"))
        self.assertTrue(analyzer("5432-5432-32-KQ3")._stop_suit_check("T1,5"))
        self.assertFalse(analyzer("5432-5432-32-KQ3")._stop_suit_check("T2"))

    def test_points_H(self):
        # 1l: number of cards was compared instead of honor points.
        self.assertTrue(analyzer("A32-5432-5432-32")._points_H_check("P>=4"))
        self.assertFalse(analyzer("A32-5432-5432-32")._points_H_check("C>=3"))


class TestRecordChecks(unittest.TestCase):
    def test_unnamed_3_cards(self):
        # 1k: named suits were checked instead of unnamed ones.
        self.assertTrue(analyzer("A32-K5-Q432-5432", *OPENED_1C)._unnamed_3_cards_check(""))
        self.assertFalse(analyzer("A3-K543-Q432-543", *OPENED_1C)._unnamed_3_cards_check(""))

    def test_has_strength_ignores_camp_suits(self):
        # 1j: a MetaSuit was searched among suit codes, so camp suits were never excluded.
        self.assertFalse(analyzer("Q32-A432-Q432-J2", *OPENED_1C)._has_strength_check())
        self.assertTrue(analyzer("K32-A432-Q432-J2", *OPENED_1C)._has_strength_check())


class TestSatisfiedBid(unittest.TestCase):
    # 2.6: rule_satisfied() modified rule.raw_bid; satisfied_bid() returns it instead.
    def test_computed_bid_is_returned_and_rule_unchanged(self):
        rule = make_rule(function_bid="best_major", arg_bid="1")
        self.assertEqual(analyzer(HAND).satisfied_bid(rule), "1P")
        self.assertEqual(rule.raw_bid, "")

    def test_fixed_raw_bid(self):
        self.assertEqual(analyzer(HAND).satisfied_bid(make_rule(raw_bid="1SA")), "1SA")

    def test_failed_condition_returns_none(self):
        self.assertIsNone(analyzer(HAND).satisfied_bid(make_rule(points="20-22H", raw_bid="2SA")))

    def test_bid_not_above_last_bid_returns_none(self):
        self.assertIsNone(analyzer(HAND, "1C", "passe").satisfied_bid(make_rule(raw_bid="1T")))

    def test_engine_returns_copy_with_computed_bid(self):
        rule = make_rule(function_bid="best_major", arg_bid="1")
        engine = BidEngine()
        engine.hand = make_hand(HAND)
        with patch.object(BidRule, "get_rules", return_value=[rule]):
            satisfied = engine._get_first_satisfied_rule("OPEN")
        self.assertEqual(satisfied.raw_bid, "1P")
        self.assertEqual(rule.raw_bid, "")

    def test_engine_returns_none_when_no_rule_satisfied(self):
        engine = BidEngine()
        engine.hand = make_hand(HAND)
        rule = make_rule(points="20-22H", raw_bid="2SA")
        with patch.object(BidRule, "get_rules", return_value=[rule]):
            self.assertIsNone(engine._get_first_satisfied_rule("OPEN"))


class TestImplicitReturns(unittest.TestCase):
    # 2.7
    def test_fit_cards_after_no_trump_is_false(self):
        result = analyzer(HAND, "1SA", "passe")._fit_cards_check(make_rule(fit_cards=">=3"))
        self.assertIs(result, False)

    def test_fit_cards_without_partner_bid_is_false(self):
        self.assertIs(analyzer(HAND)._fit_cards_check(make_rule(fit_cards=">=3")), False)

    def test_missing_sense_raises_explicit_error(self):
        rule = make_rule(raw_bid="1P", sense_id=99999)
        with patch.object(BidSense, "get", return_value=None):
            with self.assertRaisesRegex(MyDataException, "Règle 1 : sense_id 99999"):
                BidEngine()._get_bid_sense(rule)


class TestBidComputer(unittest.TestCase):
    def test_strength_skips_camp_suits(self):
        # 1j: hearts (partner's suit) was returned before spades.
        computer = BidComputer(make_hand("K32-A432-Q432-J2"), make_record(*OPENED_1C), None)
        self.assertEqual(computer.run("strength", "4"), "4P")


if __name__ == "__main__":
    unittest.main()
