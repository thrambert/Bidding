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
   numeric:    Numeric distribution or "". Example: "6322"
   special:    List of special distrib if any, or []. Example: ["bicolore 5/5"]
   ____________________________________________________________________________
   Arg for init
   value :     Either a canonical distribution in french (ex: régulier),
               either a mumeric distribution(ex: 5422),
               either a special expression (ex: bicolore 5/5).
   """
   class Main(Enum):
      REGULAR = "régulier"
      UNICOLOR = "unicolore"
      BICOLOR = "bicolore"
      TRICOLOR = "tricolore"
      UNDEFINED = "indéfini"
   

   NUM_REGULAR = [
      "4333", "4432", "5332"
      ]
   NUM_UNICOLOR = [
      "6322", "6331", "7222", "7321", "7330", "8221", "8311",
      "8320", "9211", "9220", "9310"
   ]
   NUM_BICOLOR = [
      "5422", "5431", "5521", "5530", "6421", "6430", "6511",
      "6520", "6610", "7411", "7420", "7510", "7600", "8410",
      "8500", "9400"
      ]
   NUM_TRICOLOR = [
      "4441", "5440"
      ]
   SPECIAL = {
      "bicolore 5/5":   Main.BICOLOR,     # Bicolor at least 5/5
      "bicolore 6/5":   Main.BICOLOR,     # Bicolor at least 6/5
      "semi-régulier":  Main.UNDEFINED,   # Regular or 5422 or 6322
      "irrégulier":     Main.UNDEFINED,   # Not regular
   }

   def __init__(self, input_value: str):
      self.canonical = self._get_canonical(input_value)
      self.numeric: str = input_value if input_value.isdigit() else ""
      self.special: list[str] = self._get_special()

   def get_all_shapes(self) ->list[str]:
      # Returns all expressions for this distribution, included special if any.
      shapes = [self.canonical.value]
      if self.numeric:
         shapes.append(self.numeric)
      shapes.extend(self.special)
      return shapes

   def semi_regular(self) -> bool:
      return self.canonical == self.Main.REGULAR or self.numeric in ["5422", "6322"]
   
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

   def _get_special(self) -> list[str]:
      # This function returns an item from Special.
      special_distrib = []
      # bicolore 5/5
      if self.canonical == self.Main.BICOLOR:
         if self.numeric and int(self.numeric[:2]) >= 55:
            special_distrib.append("bicolore 5/5")
         if self.numeric and int(self.numeric[:2]) >= 65:
            special_distrib.append("bicolore 6/5")         
      # semi-régulier
      if self.semi_regular():
         special_distrib.append("semi-régulier")
      # irrégulier
      if self.canonical != self.Main.REGULAR:
         special_distrib.append("irrégulier")
      return special_distrib
         
   def get_all_shapes(self) ->list[str]:
      # Returns all expressions for this distribution, included special if any.
      shapes = [self.canonical.value]
      if self.numeric:
         shapes.append(self.numeric)
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
