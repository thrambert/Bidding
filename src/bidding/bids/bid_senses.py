from __future__ import annotations

from pydantic import AfterValidator, BaseModel, Field
from typing import Annotated
from bids.files import SenseFile
from bids.bid_rules import (
   validated_points,
   validated_distrib,
   validated_suit,
   validated_count
)
from bids.bids import Forcing, SuitsToStop
from utils import MyDataException


PASS = "passe"

# =============================================================================
#  VALIDATORS
# =============================================================================

def _validated_stop_suits(value: str) -> str:
   if value and not value in [e.value for e in SuitsToStop]:
      raise MyDataException(f"{value} n'est pas une valeur de l'énumération StopSuits.")
   return value

def _validated_forcing(value: str) -> str:
   if value and not value in [e.value for e in Forcing]:
      raise MyDataException(f"{value} n'est pas une dénomination de forcing.")
   return value


class BidSense(BaseModel):
   """
   This class provides information on a bid made. This information depends on
   bidding history and is based on SEF. But it ignores detailled hand of other
   players as in real life.
   There is some redondancy with SEFrule file. But, as SEFrule may have several
   rows for the same bid, this redondancy is required.
   ____________________________________________________________________________
   Properties

   id:            Unique. May be 0 when it is created from scratch not from file.
   raw_bid:       Generic bid using symbolic suit.
   points:        An interval of points in which the player's hand is.
   distribution:  Distribution of the player's hand.
   spade_count:   Number of cards into that suit, in format <=n, >=n, or n.
   heart_count:   Idem
   diamond_count: Idem
   club_count:    Idem
   par_suit_count:Number of cards into last suit bidded by the partner.
   suit:          Suit or symbolic suit text when bid does not reveal suit.
   suit_count:    Number of cards in player suit given by his bid or by suit.
   suit_stop:     True if the player stops the suit he gave in bid or in suit.
   suit_control:  True if the player controls the suit.
   suit_force:    True if the player has a force in the suit
   stop_suits:    "opp": Stop opponent suits, "unnamed": Stop unnamed and opp suits.
   artificial:    True if the bid is not natural but a convention.
   forcing:       Indicates if the partner must bid in response.
   convention:    Name of convention.
   comment:       Additional text on bid.

   Private properties
      remark: Attributes whose name has a leading underscore are not treated as
      fields by Pydantic, and are not included in the model schema. They are not
      validated or even set during calls to __init__, model_validate, etc.
   _rule_id:      Id of rule which provided sense, or 0 if no such rule.
   """
   id: int
   raw_bid: str
   points: Annotated[str, Field(default=""), AfterValidator(validated_points)]
   distribution: Annotated[str, Field(default=""), AfterValidator(validated_distrib)]
   spade_count: Annotated[str, Field(default=""), AfterValidator(validated_count)]
   heart_count: Annotated[str, Field(default=""), AfterValidator(validated_count)]
   diamond_count: Annotated[str, Field(default=""), AfterValidator(validated_count)]
   club_count: Annotated[str, Field(default=""), AfterValidator(validated_count)]
   par_suit_count: Annotated[str, Field(default=""), AfterValidator(validated_count)]
   suit: Annotated[str, Field(default=""), AfterValidator(validated_suit)]
   suit_count: Annotated[str, Field(default=""), AfterValidator(validated_count)]
   suit_stop: bool = False
   suit_control: bool = False
   suit_force: bool = False
   stop_suits: Annotated[str, Field(default=""), AfterValidator(_validated_stop_suits)]
   artificial: bool = False
   forcing: Annotated[str, Field(default=""), AfterValidator(_validated_forcing)]
   convention: str = ""
   _rule_id = 0

   def four_suits_count(self) -> list[str]:
      return [
         self.club_count,
         self.diamond_count,
         self.heart_count,
         self.spade_count
         ]
   
   def player_suit_type(self) -> dict:
      return {
         "stop": self.suit_stop,
         "control": self.suit_control,
         "force": self.suit_force,
         }
   
   def suits_to_stop(self) -> SuitsToStop:
      return SuitsToStop.from_value(self.stop_suits) if self.stop_suits else None
   
   @classmethod
   def get(cls, id: int) -> BidSense:
      # This function reads file and sends back bid sense if found else None.
      sense_file = SenseFile(BidSense.model_fields.keys())
      row = sense_file.get_row(id)
      return cls(**row) if row else None

   @classmethod
   def passe(cls) -> BidSense:
      return cls(id=0, raw_bid=PASS)