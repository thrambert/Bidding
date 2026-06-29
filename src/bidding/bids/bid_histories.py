from __future__ import annotations

from pydantic import BaseModel
from bids.files import BidHistoryFile


# def _left_padding(text: str) -> str:
#    # Returns a 7 chr string where text left aligned and completed with spaces on right.
#    left_padding = f"{text:<7}"
#    return left_padding

# def _right_padding(text: str) -> str:
#    # Returns a 10 chr string where text is right aligned and completed with a "*"
#    #  followed by spaces on the left.
#    right_padding = f"{text:>9}"
#    return "*" + right_padding

# def _center_padding(text: str) -> str:
#    # Returns a 10 chr string where text is centered and completed with spaces
#    #  on left and on right.
#    return text.center(10, " ")

class BidHistory(BaseModel):
   """
   This class describes data stored into bid history file. 
   This file contains one single column with rule id. A rule id is written
   in file as soon as this rule is satisfied while bidding.
   A rule id is unique in file.

   Properties
   id:         id of a rule.
   """
   id: int

   def add_in_file(self):
      history_file = BidHistoryFile(BidHistory.model_fields.keys())
      bid_history = history_file.get_row(self.id)
      if not bid_history:
         history_file.add_row(self.model_dump())

   @staticmethod
   def get_all_rules_ids() -> list[int]:
      history_file = BidHistoryFile(BidHistory.model_fields.keys())
      rule_ids = history_file.get_satisfied_rules()
      rule_ids.sort()
      return rule_ids
      