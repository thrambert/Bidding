from bids.files import BidFileConverter
from bids.bid_rules import BidRule
from utils import MyDataException


def load_bid_rule_file() -> str:
   id = 1
   try:
      bid_rule_file = BidFileConverter().excel_to_Csv(BidRule.model_fields.keys())
      while id:
         row = bid_rule_file.get_row(id)
         if row:
            BidRule.model_validate(row)
            id += 1
         else:
            id = 0
   except Exception as error:
      raise MyDataException(f"    Rule {id}: {error.__str__()}")
