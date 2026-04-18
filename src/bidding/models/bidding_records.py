from typing import Annotated
from pydantic import BaseModel, AfterValidator, computed_field
from bridgebots import (
   Card,
   Deal,
   PlayerHand,
)
from bridgebots.deal_enums import (
   Direction, 
   Rank,
   Suit,
)
from bridgebots.bids import LEGAL_BIDS
from models.translators import FrenchToEnglish


def bid_validator(value: str) -> str:
   if value in LEGAL_BIDS:
      return value
   else:
      raise ValueError("Enchère non reconnue.")


class Bidding(BaseModel):
   laps: int
   rank: int
   bid: Annotated[str, AfterValidator(bid_validator)]
   rule_id: int
   
   @computed_field
   @property
   def id(self) -> str:
      return f"BID{self.laps}{self.rank}"

   @staticmethod
   def get_bid_from_str(french_bid: str) -> str:
      # This function converts bid from french to english. Example 3SA -> 3NT.
      fr_en = FrenchToEnglish()
      nbr = french_bid.pop(0) if french_bid[:1].isdigit() else ""
      bid_suit = fr_en.bid_short(french_bid)
      return nbr + bid_suit
