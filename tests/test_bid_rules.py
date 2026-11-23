import unittest

from bidding.bids.bid_rules import BidRule, validated_count, validated_points
from bidding.utils import MyDataException


def make_rule(**fields) -> BidRule:
    return BidRule(id=1, step="OPEN", opp_next_step="", camp_next_step="", **fields)


class TestBidRuleFields(unittest.TestCase):
    # 2.4
    def test_sense_id_defaults_to_int_zero(self):
        self.assertEqual(make_rule().sense_id, 0)

    def test_sense_id_none_or_empty_is_zero(self):
        self.assertEqual(make_rule(sense_id="none").sense_id, 0)
        self.assertEqual(make_rule(sense_id="").sense_id, 0)

    def test_polished_hist_bid(self):
        # The hist_bid validator requires the flag as a separate token (">> ").
        rule = make_rule(hist_bid=">> 3E passe")
        self.assertTrue(rule.hist_bid_is_partial())
        self.assertEqual(rule.polished_hist_bid(), "3E passe")
        self.assertEqual(make_rule(hist_bid="1C passe").polished_hist_bid(), "1C passe")


class TestValidatedPoints(unittest.TestCase):
    # 2.2: regex was not anchored and accepted almost anything.
    def test_valid(self):
        for value in [
            "",
            "8H",
            "11HL",
            ">12HL",
            "<=15HLD",
            "0-7H",
            "12-23HL",
            "10-16HLD",
            "16H-19HL",
            "11HL-11H",
        ]:
            self.assertEqual(validated_points(value), value)

    def test_invalid(self):
        for value in ["toto", "12", "H12", ">=11Hl", "12-23HLX", ">=12H-15HL", "5-"]:
            with self.assertRaises(MyDataException, msg=value):
                validated_points(value)


class TestValidatedCount(unittest.TestCase):
    def test_valid(self):
        for value in ["", "4", "=0", "<4", "<=1", ">3", ">=2"]:
            self.assertEqual(validated_count(value), value)

    def test_invalid(self):
        for value in ["a5", ">=", "5>", ">=2x", "=<2"]:
            with self.assertRaises(MyDataException, msg=value):
                validated_count(value)


if __name__ == "__main__":
    unittest.main()
