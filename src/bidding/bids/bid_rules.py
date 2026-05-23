from __future__ import annotations

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field
from typing import Annotated
import re
from bids.files import RuleFile
from bids.bids import Bid
from bids.hands import MetaSuit
from bids.steps import Step
from deals.distributions import Distribution
from utils import MyDataException


# =============================================================================
#  COMMON VALIDATORS ALSO USED BY SENSE 
# =============================================================================

def validated_points(value: str) -> str:
   if value and not re.search("(>=)?[1-2]?[0-9]H?(HL)?-?[1-2]?[0-9]?HL?(LD)?", value):
      raise MyDataException(f"{value} n'est pas un intervalle de points valide.")
   return value
   
def validated_distrib(value: str) -> str:
   if value and value not in Distribution.all_including_special():
      raise MyDataException(f"{value} n'est pas une distribution valide.")
   return value

def validated_suit(value: str) -> str:
   if value and not value in MetaSuit.all_texts() + MetaSuit.all_groups():
      raise MyDataException(f"{value} n'est pas une couleur valide.")
   return value

def validated_count(value: str) -> str:
   if value and not re.search(">?<?(>=)?(<=)?[1-9]", value):
      raise MyDataException(f"{value} n'est pas une condition valide sur un nombre.")
   return value
   
# =============================================================================
#  PRIVATE VALIDATORS
# =============================================================================

def _validated_step(value: str) -> str:
   if value and not value in [e.name for e in Step]:
      raise MyDataException(f"{value} n'est pas une étape valide dans le cycle des enchères.")
   return value

def _validated_bicolor(value: str) -> str:
   if value:
      for suit_name in value.split(","):
         if suit_name not in MetaSuit.all_texts():
            raise MyDataException(f"{value} n'est pas un couple de deux couleurs valides.")
   return value

def _validated_hist_bid(value: str) -> str:
   if value:
      for bid_raw in value.split(" "):
         if not Bid.valid_symbolic_bid(bid_raw):
            raise MyDataException(f"'{value}' ne correspond pas à une suite d'enchères.")
   return value

def _ensure_sense_id(value: str) -> int:
   return 0 if value in ["none", ""] else int(value)


class BidRule(BaseModel):
   """
   This class describes a rule to make a bid. These rules are based on SEF
   (Système d'Enchère Français).
   Its properties are either conditions which must all be satisfied to make
   the bid, either description data.
   ____________________________________________________________________________
   Properties used to filter rules or to describe rule

   id:            Unique id of a rule.
   step:          Bidding context in which the rule is to be applied.
   next_step:     Bidding context for the next player. If empty, use Stepping.
   ____________________________________________________________________________
   Properties as conditions

   points:        An interval of points the player's hand must be in.
   distribution:  Pattern condition the player must comply to apply the rule.
   bicolor:       A set of 2 suits in which longest suits must be.
   suit1:         Condition on longest suit of player's hand.
   suit1_count:   Condition on number of cards into longest suit.
   suit2:         Condition on 2nd longest suit.
   suit2_count:   Condition on number of cards into that suit.
   first_pass:    Condition on number of pass before opening.
   won_tricks:    Minimum number of tricks the player should realize.
   def_tricks:    Condition on number of possible won tricks out of trump.
   lost_tricks:   3 conditions on possible lost tricks, fct(vulnerability).
   fit_cards:     Condition on number of cards in partner suit.
   stops:         Required min number of stops of opponents' suits.
   awake:         True when current bid follows 2 consecutive PASS.
   hist_bid:      Required consecutive last bids.
   function'n':   Name of a function which contains a specific condition.
   arg1:          Argument for function 1
   ____________________________________________________________________________
   Properties providing the bid to make if all conditions are satisfied

   function_bid:  Name of a function to decide which bid to make in complex case.
   arg_bid:       Argument for function bid.
   raw_bid:       The bid to make if all conditions of the rule are satisfied.
   sense_id:      Id for sense of bid in SEFsense file.
   """
   id: int
   step: Annotated[str, AfterValidator(_validated_step)]
   next_step: Annotated[str, AfterValidator(_validated_step)]
   points: Annotated[str, Field(default=""), AfterValidator(validated_points)]
   distribution: Annotated[str, Field(default=""), AfterValidator(validated_distrib)]
   bicolor: Annotated[str, Field(default=""), AfterValidator(_validated_bicolor)]
   suit1: Annotated[str, Field(default=""), AfterValidator(validated_suit)]
   suit1_count: Annotated[str, Field(default=""), AfterValidator(validated_count)]
   suit2: Annotated[str, Field(default=""), AfterValidator(validated_suit)]
   suit2_count: Annotated[str, Field(default=""), AfterValidator(validated_count)]
   first_pass: str = ""
   won_tricks: float = 0
   def_tricks: Annotated[str, Field(default=""), AfterValidator(validated_count)]
   lost_tricks: int = 0
   fit_cards: Annotated[str, Field(default=""), AfterValidator(validated_count)]
   stops: float = 0
   awake: bool = False
   hist_bid: Annotated[str, Field(default=""), AfterValidator(_validated_hist_bid)]
   function1: str = ""
   function2: str = ""
   arg2: str = ""
   function_bid: str = ""
   arg_bid: str = ""
   raw_bid: str = ""
   sense_id: Annotated[int, Field(default=""), BeforeValidator(_ensure_sense_id)]

   @staticmethod
   def condition_names() -> list[str]:
      fields = list(BidRule.model_fields.keys())
      lowest = fields.index("points")
      highest = fields.index("arg2")
      return fields[lowest:highest]

   @staticmethod
   def get_rules(step_name: str) -> list[BidRule]:
      # This function reads file and sends back bid rules for given arguments.
      bid_rule_file = RuleFile(BidRule.model_fields.keys())
      rows = bid_rule_file.get_rows(step_name)
      return [BidRule(**row) for row in rows]

   def split_fit(self, partner_suit_code: str) -> tuple:
      # Returns (suit_code, partner nbr trumps, player nbr trumps)
      if not self.fit:
         return "", 0, 0
      suit_like, nbr_partner, nbr_player = self.fit.replace(" ", "").split(",")
      if suit_like == "par":
         suit_code = partner_suit_code
      elif suit_like in [s.code for s in MetaSuit.four_suits()]:
         suit_code = suit_like
      else:
         suit_code = ""
      return suit_code, int(nbr_partner), int(nbr_player)
