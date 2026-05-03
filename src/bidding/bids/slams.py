class Slam:
   """
   This class manages steps players of the same camp follow to declare a
   slam (chelem).
   We consider opposit camp in passing.
   
   Properties
   camp_ranks:       Ranks of players who are engaged in a slam process.
   fit_suit_code:    Suit code for which openers are fitted.
   splinter:         Suit code of the splinter if any.
   players_min_HLD:  Min points HLD of players engaged in slam.
   controls:         Declared suits codes the players have control on.
   """
   CONTROLS = [
      "3P",
      "4T",
      "4K",
      "4C",
      "4P",
   ]
   
   def __init__(self, rank: int, suit: str, pts_HLD: list[int], splinter: str = ""):
      self.camp_ranks = [1, 3] if rank in [1, 3] else [2, 4]
      self.fit_suit_code = suit
      self.openers_HLD:list[int] = pts_HLD
      self.splinter = splinter
      self.controls = [splinter] if splinter else []

   def next_bid(self, last_bid: str, hand_controls: list[str]) -> str:
      pass

   def lower(bid1: str, bid2: str) -> bool:
      if bid1[0] == bid2[0]:
         pass
