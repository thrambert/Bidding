"""
This module determines next step in which to compute bid for next player.
____________________________________________________________________________
Constants giving appropriate next steps

PASS:          String value of pass special bid.
R_OPEN:        Response to opening, depending on player n°2 bid.
REDEM_O:       Opener redemand in 2nd turn, depending on player n°4 bid.
INT_LAP1_NO_INT:  Steps for intervener in lap 1 when no intervention before.
INTERVENE:     Steps for interveners depending on intervention count.
WAKE:          Steps to select after 2 consecutive passes depending on rank.
____________________________________________________________________________
"""
from enum import Enum, auto
from bids.bid_records import Bidding
from utils import MyDataException


class Step(Enum):
   PASS = auto()     # impose au joueur de passer
   OPEN = auto()     # ouverture (rank 1)
   INT_N2 = auto()   # intervention du joueur n°2 (rank 2)
   SEQ1SA = auto()   # séquence du camp de l'ouvreur suite ouverture de 1SA
   SEQ2SA = auto()   # séquence du camp de l'ouvreur suite ouverture de 2SA
   SEQ2T = auto()    # séquence du camp de l'ouvreur suite ouverture de 2T
   SEQ2K = auto()    # séquence du camp de l'ouvreur suite ouverture de 2K
   STAYMAN = auto()  # séquence du camp de l'ouvreur selon convention Stayman
   TEXAS = auto()    # séquence du camp de l'ouvreur selon convention Texas
   ROSA = auto()     # autre réponse à ouverture dans le silence adverse (rank 3)
   ROACA = auto()    # autre réponse à ouverture après un contre d'appel (rank 3)
   ROAIC = auto()    # autre réponse à ouverture après intervention à la couleur (rank 3)
   ROA1SA = auto()   # autre réponse à ouverture après intervention à 1SA (rank 3)
   INT_N4 = auto()   # intervention du joueur n°4 (rank 4)
   REDOSA = auto()   # redemande de l'ouvreur dans le silence adverse (lap 2, rank 1)
   REDO = auto()     # redemande de l'ouvreur autres cas (lap 2, rank 1)
   REPINT = auto()   # réponse à intervention (lap 1 rank 4, ou lap 2 rank 2)
   REDI = auto()     # redemande de l'intervenant (lap 2 rank 2 ou 4)
   R2 = auto()       # 2e enchère du répondant après un soutien (lap 2 rank 3)
   INTEND = auto()   # suite du dialogue du camp en intervention, après REDI
   WAKE_N1 = auto()  # réveil du joueur n°1, l'ouvreur (lap 2 rank 1)
   WAKECI = auto()   # réveil du camp en intervention (lap 2 rank 2 ou 4)
   WAKE_N3 = auto()  # réveil du joueur n°3 (lap 2 rank 3)
   CHELEM = auto()   # séquence des controles, backwood et chelem


PASS = "passe"

R_OPEN = {
   PASS:    Step.ROSA,
   "X":     Step.ROACA,
   "1SA":   Step.ROA1SA,
   "other": Step.ROAIC,
}
REDEM_O = {
   PASS:    Step.REDOSA,
   "other": Step.REDO,
}
INT_LAP1_NO_INT = [
   Step.INT_N2,
   Step.INT_N4,
]
INTERVENE = [
   Step.PASS,
   Step.REPINT,
   Step.REDI,
   Step.INTEND,
]
WAKE = [
   Step.WAKECI,
   Step.WAKE_N3,
   Step.WAKECI,
   Step.WAKE_N1,
   ]

def get_next(last: Bidding, sleep: bool,
             intervene_count: int, next_step_open: str) -> str:
   # Before opening
   if not last:
      return Step.OPEN.name
   elif last.lap == 0:
      return Step.OPEN.name
   # Wake-up after two passes
   elif sleep:
      return WAKE[last.rank - 1].name
   # Intervention
   elif last.in_intervention_camp():
      return _next_step_for_opening_camp(last, next_step_open).name
   else:
      return _next_step_for_interv_camp(last, intervene_count).name

def _next_step_for_opening_camp(last: Bidding, next_step: str) -> Step:
   if next_step:
      return next_step
   elif last.lap == 1:
      return _get_value(last.bid, R_OPEN if last.rank == 2 else REDEM_O)
   elif last.lap == 2 and last.rank == 2:
      return Step.R2
   else:
      raise MyDataException("Prochaine étape du camp de l'ouvreur " + \
                              "absente après la 2e enchère du répondant")
   
def _next_step_for_interv_camp(last: Bidding, interv_count: int) -> Step:
   if last.lap == 1 and interv_count == 0:
      return INT_LAP1_NO_INT[last.rank // 3]
   else:
      # Rmk: If the 2 interveners pass in first lap, they always pass after.
      return INTERVENE[interv_count]

def _get_value(last_bid: str, step_dict: dict) -> Step:
   # Returns a step from step_dict where bid is replaced by other if not found in.
   bid = last_bid if last_bid in step_dict else "other"
   return step_dict[bid]
