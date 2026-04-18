from pydantic import AfterValidator, BaseModel, Field
from typing import Annotated

import re
from models.files import BidRuleFile
from bid_rules_enums import Forcing, Sequence, Situation, Variant
from models.hands import Distribution, SuitMeta
from utils import MyDataException


# =============================================================================
#  VALIDATORS
# =============================================================================

def _validated_variant(value: str) -> str:
   if value and not value in [e.value for e in Variant]:
      raise MyDataException(f"{value} n'est pas une variante valide.")
   return value

def _validated_situation(value: str) -> str:
   if value and not value in [e.value for e in Situation]:
      raise MyDataException(f"{value} n'est pas une situation valide.")
   return value

def _validated_sequence(value: str) -> str:
   if value and not value in [e.value for e in Sequence]:
      raise MyDataException(f"{value} n'est pas une séquence valide.")
   return value

def _validated_position(value: str) -> str:
   if value and not re.search("BID[0-9][1-4]", value):
      raise MyDataException(f"{value} n'est pas une position valide.")
   return value

def _validated_points(value: str) -> str:
   if value and not re.search("(>=)?[1-2]?[0-9]H?(HL)?-?[1-2]?[0-9]?HL?(LD)?", value):
      raise MyDataException(f"{value} n'est pas un intervalle de points valide.")
   return value
   
def _validated_distribution(value: str) -> str:
   if value:
      Distribution(value)
   return value

def _validated_bicolor(value: str) -> str:
   if value:
      for suit_name in value.split(","):
         if suit_name not in SuitMeta.FR_SUIT.keys():
            raise MyDataException(f"{value} n'est pas un couple de deux couleurs valides.")
   return value

def _validated_color(value: str) -> str:
   if value and not value in list(SuitMeta.FR_SUIT.keys()) + list(SuitMeta.GROUP.values()):
      raise MyDataException(f"{value} n'est pas une couleur valide.")
   return value

def _validated_count(value: str) -> str:
   if value and not re.search(">?<?(>=)?(<=)?[1-9]", value):
      raise MyDataException(f"{value} n'est pas une condition valide sur un nombre.")
   return value
   
def _validated_hist_bid(value: str) -> str:
   if value and not re.search("BID[0-9][1-4]=[1-7]?[PCKTMmASX][AX]?(SSE)?", value):
      raise MyDataException(f"{value} n'est pas une enchère antérieure.")
   return value

def _validated_forcing(value: str) -> str:
   if value and not value in [e.value for e in Forcing]:
      raise MyDataException(f"{value} n'est pas une dénomination de forcing.")
   return value


class BidRule(BaseModel):
   """
   This class describes a rule to make a bid. These rules are based on SEF
   (Système d'Enchère Français).
   Its properties are either conditions which must all be satisfied to make
   the bid, either description data.
   ____________________________________________________________________________
   Descriptive properties or used to filter rules

   id:            Unique id of a rule.
   SEF_page:      The page where rule is described in book SEF 2024.
   variant:       A variant in addition of SEF.
   situation:     Bidding context in which the rule is to be applied.
   sequence:      A flag to group together rules which follow a known sequence.
   ____________________________________________________________________________
   Properties as conditions

   position:      The position in which the player must be to apply the rule.
   points:        An interval of points the player's hand must be in.
   distribution:  Pattern condition the player must comply to apply the rule.
   bicolor:       A set of 2 suits in which longest suits must be.
   color1:        Condition on longest suit of player's hand.
   color1_count:  Condition on number of cards into longest suit.
   color2:        Condition on 2nd longest suit.
   color2_count:  Condition on number of cards into that suit.
   won_tricks:    Minimum number of tricks the player should realize.
   def_tricks:    Condition on number of possible won tricks out of trump.
   lost_tricks:   3 conditions on possible lost tricks, fct(vulnerability).
   fit_cards:     Condition on number of cards in partner suit.
   awake:         True when current bid follows 2 consecutive PASS.
   hist_bid:      Condition on a previous bid.
   function'n':   Name of a function which contains a specific condition.
   ____________________________________________________________________________
   Properties providing the bid to make if all conditions are satisfied

   function_bid:  Name of a function to decide which bid to make in complex case.
   bid:           The bid to make if all conditions of the rule are satisfied.
   ____________________________________________________________________________
   Descriptive properties on the bid

   symbolic_bid:  Generic bid where suit may be replaced by Majeure or mineure.
   artificial:    True if the bid is not natural but a convention.
   forcing:       Indicates if the partner must bid in response.
   convention:    Name of main conventions.
   """
   id: int
   SEF_page: int = 0 
   variant: Annotated[str, Field(default=""), AfterValidator(_validated_variant)]
   situation: Annotated[str, AfterValidator(_validated_situation)]
   sequence: Annotated[str, Field(default=""), AfterValidator(_validated_sequence)]
   position: Annotated[str, Field(default=""), AfterValidator(_validated_position)]
   points: Annotated[str, Field(default=""), AfterValidator(_validated_points)]
   distribution: Annotated[str, Field(default=""), AfterValidator(_validated_distribution)]
   bicolor: Annotated[str, Field(default=""), AfterValidator(_validated_bicolor)]
   color1: Annotated[str, Field(default=""), AfterValidator(_validated_color)]
   color1_count: Annotated[str, Field(default=""), AfterValidator(_validated_count)]
   color2: Annotated[str, Field(default=""), AfterValidator(_validated_color)]
   color2_count: Annotated[str, Field(default=""), AfterValidator(_validated_count)]
   won_tricks: float = 0
   def_tricks: Annotated[str, Field(default=""), AfterValidator(_validated_count)]
   lost_tricks: int = 0
   fit_cards: Annotated[str, Field(default=""), AfterValidator(_validated_count)]
   awake: bool = False
   hist_bid: Annotated[str, Field(default=""), AfterValidator(_validated_hist_bid)]
   function1: str = ""
   function2: str = ""
   function3: str = ""
   function_bid: str = ""
   bid: str = ""
   symbolic_bid: str = ""
   artificial: bool = False
   forcing: Annotated[str, Field(default=""), AfterValidator(_validated_forcing)]
   convention: str = ""

   @staticmethod
   def condition_names() -> list[str]:
      fields = list(BidRule.model_fields.keys())
      lowest = fields.index("position")
      highest = fields.index("function_bid")
      return fields[lowest:highest]

   @staticmethod
   def get_rules(situation: str, sequence: str) -> list:
      # This function reads file and sends back bid rules for given arguments.
      bid_rule_file = BidRuleFile(BidRule.model_fields.keys())
      rows = bid_rule_file.get_rows(situation, sequence)
      return [BidRule(**row) for row in rows]

