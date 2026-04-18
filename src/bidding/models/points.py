from pydantic import BaseModel
import re


def matching(math_inequality: str, value: int) -> bool:
   """
   Value and math inequality (<n, <=n, >n, >=n) are concatenate to get a math
   expression, example: 'value<=n'. If math inequality is only a number, == is
   added in between. The math expression is then evaluated.
   """
   
   equals = "==" if math_inequality[0].isdigit() else ""
   expression = str(value) + equals + math_inequality
   return eval(expression)


class PointZone:
   """
   This class provides a zone of points for player's hand.
   ____________________________________________________________________________
   Properties
   min:        min value included
   max:        max value included
   type_min:   type of points for min value H, HL or HLD
   type_max:   same for max value
   """
   def __init__(self, zone_of_points: str):
      self.min: int = 0
      self.max: int = 40
      self.type_min: str = "H"
      self.type_max: str = "H"
      self._load_attributes(zone_of_points)

   def _load_attributes(self, zone_of_points: str):
      """
      Argument zone_of_points may follow one of patterns below :
      a) nnH, nnHL, or nnHLD  -> means equals nnH...
      b) OPnnH, OPnnHL, or OPnnHLD
      c) nn-ppH, nn-ppHL, or nn-ppHLD
      d) nnH-ppHL, or nnHL-ppH
      where    OP is <, >, <=, >=
               nn, pp are numbers from 0 to 40, and nn < pp
               H, HL, HLD are ways to count points of a hand in bridge.
      """
      op = re.match(r'[<>]=?', zone_of_points)
      numbers = re.findall(r'\d+', zone_of_points)
      types = re.findall(r'HL?D?', zone_of_points)
      self._load_types(types)
      if op:
         self._load_values_with_inequality(str(op.group()), int(numbers[0]))
      else:
         self._load_values_without_inequality(numbers)

   def _load_types(self, types: list):
      self.type_min = types[0]
      self.type_max = types[1] if len(types) == 2 else self.type_min

   def _load_values_with_inequality(self, op: str, number: int):
      if op[:1] == ">":
         self.min = number + (0 if op == ">=" else 1)
      elif op[:1] == "<":
         self.max = number + (0 if op == "<=" else -1)

   def _load_values_without_inequality(self, numbers: list):
      self.min = int(numbers[0])
      self.max = int(numbers[1]) if len(numbers) == 2 else self.min

   def is_HLD(self) -> bool:
      return self.type_min == "HLD" and self.type_max == "HLD"
   
   def contains(self, pts_H: int, pts_HL: int) -> bool:
      if self.is_HLD():
         print("error in PointZone, should use HLD")
      player_min = pts_H if self.type_min == "H" else pts_HL
      player_max = pts_H if self.type_max == "H" else pts_HL
      return player_min >= self.min and player_max <= self.max

   def contains_HLD(self, pts_HLD: int) -> bool:
      if not self.is_HLD:
         print("error in PointZone, should not use HLD")
      return pts_HLD >= min and pts_HLD <= max
