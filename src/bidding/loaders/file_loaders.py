from models.files import BidFileConverter
from models.bid_rules import BidRule


def load_bid_rule_file() -> str:
   try:
      bid_rule_file = BidFileConverter().excel_to_Csv(BidRule.model_fields.keys())
      id = 1
      while id:
         row = bid_rule_file.get_row(id)
         if row:
            id += 1
            BidRule.model_validate(row)
         else:
            id = 0
   except Exception as error:
      raise error
