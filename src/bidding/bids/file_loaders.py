from bids.files import BidHistoryFile, ExcelToCsv
from bids.bid_rules import BidRule
from bids.bid_senses import BidSense
from bids.bid_histories import BidHistory
from utils import MyDataException


class FileLoader:
   CONVERTER = {
      "Rule": (ExcelToCsv().convert_rules, BidRule),
      "Bid":  (ExcelToCsv().convert_senses, BidSense),
   }

   def run(self):
      self._create_bid_history_file_if_none()
      for name, value in self.CONVERTER.items():
         self._create_csv_file_from_excel(name, value[0], value[1])

   def _create_csv_file_from_excel(self, name: str, convert_fct: any, a_class: type) -> str:
      id = 1
      try:
         csv_file = convert_fct(a_class.model_fields.keys())
         while id:
            row = csv_file.get_row(id)
            if row:
               a_class.model_validate(row)
               id += 1
            else:
               id = 0
      except Exception as error:
         raise MyDataException(f"File loader exception for {name} {id}: {error.__str__()}")

   def _create_bid_history_file_if_none(self):
      bid_history_file = BidHistoryFile(BidHistory.model_fields.keys())
      if not bid_history_file.exists():
         bid_history_file.recreate()
