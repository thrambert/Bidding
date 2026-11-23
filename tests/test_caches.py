import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from bidding.bids.bid_histories import BidHistory
from bidding.bids.bid_rules import BidRule
from bidding.bids.bid_senses import BidSense
from bidding.bids.file_loaders import FileLoader
from bidding.bids.files import CsvFile
from bidding.utils import Asset

RULE_DEFAULTS = {"opp_next_step": "", "camp_next_step": "", "won_tricks": 0, "stops": 0}
SENSE_DEFAULTS = {f: False for f in ["suit_stop", "suit_control", "suit_force", "artificial"]}


class TempAssetsTestCase(unittest.TestCase):
    """Points Asset to a temporary project root, and resets rule and sense caches."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        (Path(tmp.name) / "assets").mkdir()
        self.addCleanup(setattr, Asset, "project_root", Asset.project_root)
        Asset.project_root = Path(tmp.name)
        for clear in (BidRule.clear_cache, BidSense.clear_cache):
            clear()
            self.addCleanup(clear)

    @staticmethod
    def write_csv(name: str, fields, rows: list[dict]):
        csv_file = CsvFile(Asset.path(name), list(fields))
        csv_file.recreate()
        csv_file.add_rows(rows)

    def write_rules(self, *rules: tuple[int, str, str]):
        rows = [{**RULE_DEFAULTS, "id": i, "step": step, "raw_bid": bid} for i, step, bid in rules]
        self.write_csv("bid_rules.csv", BidRule.model_fields, rows)

    def write_senses(self, *senses: tuple[int, str]):
        rows = [{**SENSE_DEFAULTS, "id": i, "raw_bid": bid} for i, bid in senses]
        self.write_csv("bid_senses.csv", BidSense.model_fields, rows)


class TestRuleCache(TempAssetsTestCase):
    def setUp(self):
        super().setUp()
        self.write_rules((1, "OPEN", "1SA"), (2, "INT_N2", "X"), (3, "OPEN", "1C"))

    def test_rules_by_step_in_file_order(self):
        self.assertEqual([r.id for r in BidRule.get_rules("OPEN")], [1, 3])
        self.assertEqual([r.id for r in BidRule.get_rules()], [1, 2, 3])
        self.assertEqual(BidRule.get_rules("WAKE"), [])

    def test_file_read_once_until_cache_cleared(self):
        BidRule.get_rules("OPEN")
        self.write_rules((1, "OPEN", "2SA"))
        self.assertEqual(BidRule.get_rules("OPEN")[0].raw_bid, "1SA")
        BidRule.clear_cache()
        self.assertEqual(BidRule.get_rules("OPEN")[0].raw_bid, "2SA")

    def test_returned_list_does_not_alter_cache(self):
        BidRule.get_rules("OPEN").clear()
        self.assertEqual(len(BidRule.get_rules("OPEN")), 2)

    def test_rules_are_frozen(self):
        rule = BidRule.get_rules("OPEN")[0]
        with self.assertRaises(ValidationError):
            rule.raw_bid = "7SA"
        self.assertEqual(rule.model_copy(update={"raw_bid": "7SA"}).raw_bid, "7SA")

    def test_last_id(self):
        self.assertEqual(BidRule.get_last_id(), 3)
        self.write_rules()
        BidRule.clear_cache()
        self.assertEqual(BidRule.get_last_id(), 0)


class TestSenseCache(TempAssetsTestCase):
    def setUp(self):
        super().setUp()
        self.write_senses((10, "1C"), (11, "1P"))

    def test_get(self):
        self.assertEqual(BidSense.get(11).raw_bid, "1P")
        self.assertIsNone(BidSense.get(99))

    def test_get_returns_a_copy(self):
        sense = BidSense.get(10)
        sense.raw_bid = "2C"
        sense._rule_id = 5
        fresh = BidSense.get(10)
        self.assertEqual((fresh.raw_bid, fresh._rule_id), ("1C", 0))

    def test_file_read_once_until_cache_cleared(self):
        BidSense.get(10)
        self.write_senses((10, "2T"))
        self.assertEqual(BidSense.get(10).raw_bid, "1C")
        BidSense.clear_cache()
        self.assertEqual(BidSense.get(10).raw_bid, "2T")


class TestFileLoaderClearsCaches(TempAssetsTestCase):
    def test_run_reloads_rewritten_files(self):
        self.write_rules((1, "OPEN", "1SA"))
        self.write_senses((10, "1C"))
        BidRule.get_rules(), BidSense.get(10)
        self.write_rules((1, "OPEN", "2SA"), (2, "OPEN", "1T"))
        self.write_senses((10, "2C"))
        with (
            patch.object(FileLoader, "_create_csv_file_from_excel"),
            patch.object(FileLoader, "_create_bid_history_file_if_none"),
        ):
            FileLoader().run()
        self.assertEqual([r.raw_bid for r in BidRule.get_rules()], ["2SA", "1T"])
        self.assertEqual(BidSense.get(10).raw_bid, "2C")


class TestBidHistory(TempAssetsTestCase):
    def setUp(self):
        super().setUp()
        self.write_csv("bid_history.csv", BidHistory.model_fields, [])

    def file_ids(self) -> list[str]:
        return Asset.path("bid_history.csv").read_text().split()[1:]

    def test_adds_new_ids_once_in_given_order(self):
        BidHistory.add_all_in_file([3, 1, 3])
        BidHistory.add_all_in_file(iter([1, 2]))
        self.assertEqual(self.file_ids(), ["3", "1", "2"])
        self.assertEqual(BidHistory.get_all_rules_ids(), [1, 2, 3])

    def test_single_write_per_call(self):
        calls = []
        original = CsvFile.add_rows

        def spy(csv_file, rows):
            calls.append(rows)
            original(csv_file, rows)

        with patch.object(CsvFile, "add_rows", spy):
            BidHistory.add_all_in_file([5, 6, 7])
            BidHistory.add_all_in_file([5, 6])
        self.assertEqual(calls, [[{"id": 5}, {"id": 6}, {"id": 7}]])


if __name__ == "__main__":
    unittest.main()
