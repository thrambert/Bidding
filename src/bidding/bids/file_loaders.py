from collections.abc import Callable

from pydantic import BaseModel

from bidding.bids.bid_histories import BidHistory
from bidding.bids.bid_rules import BidRule
from bidding.bids.bid_senses import BidSense
from bidding.bids.files import BidHistoryFile, ExcelToCsv
from bidding.utils import MyDataException


class FileLoader:
    CONVERTER = {
        "Rule": (ExcelToCsv().convert_rules, BidRule),
        "Sense": (ExcelToCsv().convert_senses, BidSense),
    }

    def run(self):
        self._create_bid_history_file_if_none()
        for name, value in self.CONVERTER.items():
            self._create_csv_file_from_excel(name, value[0], value[1])
        # CSV files have been rewritten: rules and senses must be read again.
        BidRule.clear_cache()
        BidSense.clear_cache()
        self._check_Rule_ids_sequence()

    def _create_csv_file_from_excel(
        self, name: str, convert_fct: Callable, a_class: type[BaseModel]
    ) -> None:
        row_id = 1
        try:
            csv_file = convert_fct(a_class.model_fields.keys())
            for row in csv_file.get_rows():
                row_id = row["id"]
                a_class.model_validate(row)
        except Exception as error:
            raise MyDataException(
                f"File loader exception for {name} at id {row_id} --> {error}"
            ) from error

    def _check_Rule_ids_sequence(self):
        id = 1
        gap_msg = "File loader exception for Rule: Gap between"
        for rule in BidRule.get_rules():
            if rule.id != id:
                raise MyDataException(f"{gap_msg} lines of id {id - 1} and {rule.id}.")
            else:
                id += 1

    def _create_bid_history_file_if_none(self):
        bid_history_file = BidHistoryFile(BidHistory.model_fields.keys())
        if not bid_history_file.exists():
            bid_history_file.recreate()
