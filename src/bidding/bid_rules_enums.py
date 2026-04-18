from __future__ import annotations

from enum import Enum


class Variant(Enum):
   TWO_ON_ONE = "2/1 forcing manche"


class Situation(Enum):
   OPEN = "ouverture"
   ROSA = "ROSA"
   INTER = "intervention"
   SEQUENCE = "séquence"


class Sequence(Enum):
   NT1 = "1SA"


class Forcing(Enum):
   ONCE = "forcing"
   MANCHE = "manche"
   AUTO = "autoforcing"

   def __repr__(self) -> str:
      match self:
         case self.ONCE:
            return "forcing pour 1 tour"
         case self.MANCHE:
            return "forcing de manche"
         case self.AUTO:
            return "forcing et autoforcing"
