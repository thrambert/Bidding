import tempfile
import unittest
from pathlib import Path

from bidding.bids.bid_rules import BidRule
from bidding.bids.file_loaders import FileLoader
from bidding.bids.files import CsvFile
from bidding.utils import MyDataException, MyFileAccessException


class TestCsvFileErrors(unittest.TestCase):
    # 2.5: OSError was not caught by recreate(), and messages were split into chars.
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.missing_dir_file = CsvFile(Path(self.tmp.name) / "missing" / "f.csv", ["id"])

    def test_recreate_wraps_os_error(self):
        with self.assertRaises(MyFileAccessException) as ctx:
            self.missing_dir_file.recreate()
        self.assertIsInstance(ctx.exception.__cause__, OSError)
        self.assertEqual(ctx.exception.args, (ctx.exception.msg,))

    def test_add_row_wraps_os_error(self):
        with self.assertRaises(MyFileAccessException) as ctx:
            self.missing_dir_file.add_row({"id": 1})
        self.assertIsInstance(ctx.exception.__cause__, OSError)

    def test_add_row_wraps_unknown_field(self):
        csv_file = CsvFile(Path(self.tmp.name) / "f.csv", ["id"])
        csv_file.recreate()
        with self.assertRaises(MyFileAccessException) as ctx:
            csv_file.add_row({"id": 1, "unknown": 2})
        self.assertIsInstance(ctx.exception.__cause__, ValueError)

    def test_recreate_then_add_row(self):
        csv_file = CsvFile(Path(self.tmp.name) / "f.csv", ["id"])
        csv_file.recreate()
        csv_file.add_row({"id": 7})
        self.assertEqual(csv_file.get_rows(), [{"id": "7"}])


class TestFileLoaderErrors(unittest.TestCase):
    def test_original_error_is_chained(self):
        def failing_convert(fields):
            raise OSError("disk full")

        with self.assertRaises(MyDataException) as ctx:
            FileLoader()._create_csv_file_from_excel("Rule", failing_convert, BidRule)
        self.assertIsInstance(ctx.exception.__cause__, OSError)
        self.assertIn("disk full", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
