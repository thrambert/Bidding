from __future__ import annotations

from enum import Enum
from utils import MyDataException


class Distribution:
   """
   This class manages player's hand distribution to support bidding rules, that is
   to determine which bid to make.
   ____________________________________________________________________________
   Properties
   canonical : One Main enum, see below
   ordinal:    Ordinal distribution or "". Example: "6-3-2-2"
   special:    List of special distrib if any, or []. Example: ["bicolore 5/5"]
   ____________________________________________________________________________
   Arg for init
   value :     Either a canonical distribution in french (ex: régulier),
               either a mumeric distribution(ex: 5-4-2-2),
               either a special expression (ex: bicolore 5/5).
   """
   class Main(Enum):
      REGULAR = "régulier"
      UNICOLOR = "unicolore"
      BICOLOR = "bicolore"
      TRICOLOR = "tricolore"
      UNDEFINED = "indéfini"
   

   NUM_REGULAR = [
      "4-3-3-3", "4-4-3-2", "5-3-3-2"
      ]
   NUM_UNICOLOR = [
      "6-3-2-2", "6-3-3-1", "7-2-2-2", "7-3-2-1", "7-3-3-0", "8-2-2-1", "8-3-1-1",
      "8-3-2-0", "9-2-1-1", "9-2-2-0", "9-3-1-0", "10-1-1-1", "10-2-1-0",
      "10-3-0-0", "11-1-1-0", "11-2-0-0", "12-1-0-0", "13-0-0-0"
      ]
   NUM_BICOLOR = [
      "5-4-2-2", "5-4-3-1", "5-5-2-1", "5-5-3-0", "6-4-2-1", "6-4-3-0", "6-5-1-1",
      "6-5-2-0", "6-6-1-0", "7-4-1-1", "7-4-2-0", "7-5-1-0", "7-6-0-0", "8-4-1-0",
      "8-5-0-0", "9-4-0-0"
      ]
   NUM_TRICOLOR = [
      "4-4-4-1", "5-4-4-0"
      ]
   SPECIAL = {
      "bicolore 5/5":   Main.BICOLOR,     # Bicolor at least 5/5
      "bicolore 6/5":   Main.BICOLOR,     # Bicolor at least 6/5
      "semi-régulier":  Main.UNDEFINED,   # Regular or 5-4-2-2 or 6-3-2-2
      "irrégulier":     Main.UNDEFINED,   # Not regular
   }

   def __init__(self, value: str):
      self.canonical = self._get_canonical(value)
      self.ordinal: str = value if value[0].isdigit() else ""
      self.special = [value] if value in self.SPECIAL.keys() else []
      self._complete_special()

   def get_all_shapes(self) ->list[str]:
      # Returns all expressions for this distribution, included special if any.
      shapes = [self.canonical.value]
      if self.ordinal:
         shapes.append(self.ordinal)
      shapes.extend(self.special)
      return shapes

   def semi_regular(self) -> bool:
      return self.canonical == self.Main.REGULAR \
         or self.ordinal in ["5-4-2-2", "6-3-2-2"] \
         or "semi-régulier" in self.special
   
   def _get_canonical(self, input_value: str) -> Main:
      # Returns a Main enum, or None.
      if input_value in [e.value for e in self.Main]:
         return self.Main(input_value)
      elif input_value in self.NUM_REGULAR:
         return self.Main.REGULAR
      elif input_value in self.NUM_UNICOLOR:
         return self.Main.UNICOLOR
      elif input_value in self.NUM_BICOLOR:
         return self.Main.BICOLOR
      elif input_value in self.NUM_TRICOLOR:
         return self.Main.TRICOLOR
      elif input_value in self.SPECIAL.keys():
         return self.SPECIAL[input_value]
      else:
         raise MyDataException(f"La distribution {input_value} est incorrecte.")

   def _complete_special(self):
      # This function adds items in self.special.
      # bicolore 5/5
      if self.canonical == self.Main.BICOLOR:
         numeric = self.ordinal.replace("-", "")
         suffix = int(numeric[:2]) if numeric else 0
         if suffix >= 55:
            self.special.append("bicolore 5/5")
         if suffix >= 65:
            self.special.append("bicolore 6/5")         
      # semi-régulier
      if self.semi_regular():
         self.special.append("semi-régulier")
      # irrégulier
      if self.canonical != self.Main.REGULAR:
         self.special.append("irrégulier")
      # remove duplicates
      self.special = list(set(self.special))
         
   def get_all_shapes(self) ->list[str]:
      # Returns all expressions for this distribution, included special if any.
      shapes = [self.canonical.value]
      if self.ordinal:
         shapes.append(self.ordinal)
      shapes.extend(self.special)
      return shapes

   @staticmethod
   def all_including_special() -> list[str]:
      all = [e.value for e in Distribution.Main]
      all += Distribution.NUM_REGULAR
      all += Distribution.NUM_UNICOLOR
      all += Distribution.NUM_BICOLOR
      all += Distribution.NUM_TRICOLOR
      all += Distribution.SPECIAL
      return all
