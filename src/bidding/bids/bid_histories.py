from enum import Enum
from functools import reduce
from pydantic import AfterValidator, BaseModel
from typing import Annotated
from bids.files import BidHistoryFile
from utils import MyDataException, MyFileAccessException


def _left_padding(text: str) -> str:
   # Returns a 7 chr string where text left aligned and completed with spaces on right.
   left_padding = f"{text:<7}"
   return left_padding

def _right_padding(text: str) -> str:
   # Returns a 10 chr string where text is right aligned and completed with a "*"
   #  followed by spaces on the left.
   right_padding = f"{text:>9}"
   return "*" + right_padding

def _center_padding(text: str) -> str:
   # Returns a 10 chr string where text is centered and completed with spaces
   #  on left and on right.
   return text.center(10, " ")

def _validated_row_type(value: str) -> str:
   if value and not value in [e.name for e in _RowType]:
      raise MyDataException(f"{value} is not a valid row type for bid history file.")
   return value


class _RowType(Enum):
   DEAL = 0
   DIRS = 1
   BIDS = 2
   RULE = 3

   @classmethod
   def from_name(cls, name: str):
      for type in _RowType:
         if type.name == name:
            return type


class BidHistory(BaseModel):
   """
   This class describes data stored into bid history file. This file contains
   hands and for each hand the bids made and related applied rule.
   Structure of a row in file: deal id;type of row;content
   
   Content depends on type of row as below:
   DEAL ->  Cards of 4 hands North, East, South, West,
            inside one hand cards are sorted by suit (spade to club),
            from Ace to 2, each card is figured by one chr.
            Example:
            'AKQ9-Q9-KQJ98-A4, 6-J8763-T75-Q982, J854-A2-A6-KJ653, T732-KT54-432-T7'
   DIRS ->  'North  East   South  West'
   BIDS ->  '1P     passe  1SA    2T'   as an example
   RULE ->  '8             114    528'  as an example
   Rows BIDS and RULE are repeated for each lap related to a given deal.

   Properties
   deal_id:    9 chr string with an number right justified filled by "*" + 
               spaces on left.
   type:       4 chr string describing type of row.
   content:    content depending of row type, see upper.

   Private properties
      remark: Attributes whose name has a leading underscore are not treated as
      fields by Pydantic, and are not included in the model schema. They are not
      validated or even set during calls to __init__, model_validate, etc.
   _bids:  chronological list of raw bids made, including first pass if any.
   _rules: id of rules related to bids. When a rule refers to no bid, rule = 0.
   """
   deal_id: str = ""
   type: Annotated[str, AfterValidator(_validated_row_type)]
   content: str
   _bids: list[str] = []
   _rules: list[int] = []

   @staticmethod
   def get_all_rules() -> set:
      rules = []
      history_file = BidHistoryFile(BidHistory.model_fields.keys())
      for row in history_file.get_rule_rows():
         bid_history = BidHistory(**row)
         rules.extend(bid_history._get_rules())
      unique_rules = list(set(rules))
      unique_rules.sort()
      return unique_rules

   @staticmethod
   def add_deal_to_file(short_cards: list[str]):
      # arg is a list of card codes, as "AKQ9876-K92-K9-A" representing cards
      #  in spades, hearts, diamonds and clubs for a hand.
      text = reduce(lambda x, y: x + ", " + y, short_cards)
      bid_history = BidHistory(type=_RowType.DEAL.name, content=text)
      bid_history._add_to_file()
   
   @staticmethod
   def add_dirs_title_to_file():
      _DIRS_TEXT = "  North      East     South      West"
      bid_history = BidHistory(type=_RowType.DIRS.name, content=_DIRS_TEXT)
      bid_history._add_to_file()
   
   @staticmethod
   def add_bids_and_rules_to_file(bids: list[str], rules: list[int]):
      """
      bids:    chronological list of raw bids made, including first pass if any.
      rules:   id of rules related to bids. 0 when a rule refers to no bid.
      """
      for i in range(0, len(bids), 4):
         j = min(i + 4, len(bids))
         BidHistory._add_bids_row_to_file(bids[i:j])
         BidHistory._add_rules_row_to_file(rules[i:j])

   @staticmethod
   def _add_bids_row_to_file(bids: list[str]):
      text = ""
      for bid in bids:
         text += _center_padding(bid)    
      bid_history = BidHistory(type=_RowType.BIDS.name, content=text)
      bid_history._add_to_file()
   
   @staticmethod
   def _add_rules_row_to_file(rules: list[int]):
      text = ""
      for rule in rules:
         text += _center_padding(str(rule) if rule else "")
      bid_history = BidHistory(type=_RowType.RULE.name, content=text)
      bid_history._add_to_file()
   
   @classmethod
   def _get_last(cls):
      history_file = BidHistoryFile(BidHistory.model_fields.keys())
      row = history_file.get_last_row()
      return cls(**row) if row else None

   def _add_to_file(self):
      history_file = BidHistoryFile(BidHistory.model_fields.keys())
      self.deal_id = self._compute_next_row_deal_id()
      try:
         history_file.add_row(self.model_dump())
      except MyFileAccessException as error:
         raise error
   
   def _row_type(self) -> _RowType:
      return _RowType.from_name(self.type)

   def _deal_id_int(self) -> int:
      return int(self.deal_id[1:].strip())
   
   def _get_rules(self) -> list[int]:
      if self._row_type() == _RowType.RULE:
         rules_text = self.content.strip()
         return [int(r) for r in rules_text.split()]
   
   def _compute_next_row_deal_id(self) -> str:
      last = BidHistory._get_last()
      if not last:
         return _right_padding("1")
      elif self._row_type() == _RowType.DEAL:
         deal_id_int = int(last.deal_id[1:].strip())
         next_id = deal_id_int + 1
         return _right_padding(str(next_id))
      else:
         return last.deal_id
      