"""
bridge_lark_grammar.py
======================
Grammaire Lark pour les enchères du bridge, avec transformateur
vers les objets de la bibliothèque bridgebots.
 
Structures bridgebots couvertes :
  - Suit          → Enum  : CLUBS, DIAMONDS, HEARTS, SPADES
  - Direction     → Enum  : NORTH, EAST, SOUTH, WEST
  - Rank          → Enum  : TWO … ACE
  - Card          → dataclass(rank: Rank, suit: Suit)
  - Bid           → dataclass(level: int, suit: Suit | None)  # None = Sans-Atout
  - BidAnnotation → dataclass(alert: bool, explanation: str | None)
  - BidRecord     → list[(Direction, Bid, BidAnnotation | None)]
  - BoardRecord   → deal + bidding metadata
 
Installation :
    pip install bridgebots lark
 
Usage rapide :
    parser = build_parser()
    result = parser.parse(EXEMPLE_PBN)
    board  = BridgeTransformer().transform(result)
"""

from __future__ import annotations
 
# ─── Imports standard ─────────────────────────────────────────────────────────
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
 
# ─── Lark ─────────────────────────────────────────────────────────────────────
from lark import Lark, Transformer, v_args, Token, Tree
 
# ─── bridgebots ───────────────────────────────────────────────────────────────
# NOTE : toutes les classes sont importées depuis bridgebots.
#        En cas d'absence du paquet, des substituts dataclass sont utilisés
#        pour les tests hors-ligne.
try:
    from bridgebots import Suit, Direction, Rank, Card
    from bridgebots.deal import BidRecord, BoardRecord
    from bridgebots.bidding import Bid, BidAnnotation
    _BRIDGEBOTS = True
except ImportError:
    _BRIDGEBOTS = False
 
    # ── Substituts légers (si bridgebots absent) ──────────────────────────────
    from enum import Enum
 
    class Suit(Enum):
        CLUBS    = "C"
        DIAMONDS = "D"
        HEARTS   = "H"
        SPADES   = "S"
 
    class Direction(Enum):
        NORTH = "N"
        EAST  = "E"
        SOUTH = "S"
        WEST  = "W"
 
    class Rank(Enum):
        TWO   = "2"; THREE = "3"; FOUR  = "4"; FIVE  = "5"
        SIX   = "6"; SEVEN = "7"; EIGHT = "8"; NINE  = "9"
        TEN   = "T"; JACK  = "J"; QUEEN = "Q"; KING  = "K"; ACE = "A"
 
    @dataclass
    class Card:
        rank: Rank
        suit: Suit
 
    @dataclass
    class Bid:
        level: int          # 1–7, ou 0 pour PASS / DOUBLE / REDOUBLE
        suit:  Optional[Suit] = None   # None = Sans-Atout, "PASS", "X", "XX"
        call:  Optional[str]  = None   # "PASS" | "X" | "XX" | None
 
    @dataclass
    class BidAnnotation:
        alert:       bool
        explanation: Optional[str] = None
 
    @dataclass
    class BidRecord:
        dealer:     Direction
        bids:       List[Tuple[Bid, Optional[BidAnnotation]]] = field(default_factory=list)
 
    @dataclass
    class BoardRecord:
        board_num:  int
        dealer:     Direction
        vulnerable: str
        hands:      dict          # Direction → List[Card]
        bid_record: BidRecord
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  GRAMMAIRE LARK
# ═══════════════════════════════════════════════════════════════════════════════
 
BRIDGE_GRAMMAR = r"""
    // =========================================================
    //  Grammaire Bridge — enchères & distribution
    //  Compatible bridgebots  •  Lark LALR + lexer contextuel
    // =========================================================
 
    start       : board_record+
 
    // ── Donne complète (balises PBN) ─────────────────────────────────────────
    board_record : board_tag
                   dealer_tag
                   vul_tag
                   deal_tag
                   auction_tag
 
    board_tag    : "[Board"      NUMBER      "]"
    dealer_tag   : "[Dealer"     direction   "]"
    vul_tag      : "[Vulnerable" vul         "]"
    deal_tag     : "[Deal"       pbn_deal    "]"
    auction_tag  : "[Auction"    direction   "]" auction
 
    // ── Distribution PBN ─────────────────────────────────────────────────────
    // Format :  direction ":" main main main main
    // Chaque main = spades.hearts.diamonds.clubs (cartes hautes puis basses)
    // ex : N:AKQ.JT9.8765.432 T98.AKQ.AKQJ.KQJ ...
    pbn_deal    : direction ":" pbn_hand pbn_hand pbn_hand pbn_hand
    pbn_hand    : pbn_suit "." pbn_suit "." pbn_suit "." pbn_suit /[ ]/?
    pbn_suit    : CARD_CHAR*                  // vide = chicane
    CARD_CHAR   : /[AKQJT98765432x]/
 
    // ── Séquence d'enchères ──────────────────────────────────────────────────
    auction          : annotated_call+
    annotated_call   : call annotation?
 
    // Annotation attachée à une enchère
    annotation  : ALERT_MARK                  -> alert
                | NOALERT_MARK                -> no_alert
                | "{" EXPL_TEXT "}"           -> explanation
    ALERT_MARK  : "!"
    NOALERT_MARK: "="
    EXPL_TEXT   : /[^}]*/
 
    // ── Appel individuel ─────────────────────────────────────────────────────
    ?call       : bid | special_call
 
    // Enchère = niveau (1–7) + couleur ou Sans-Atout
    bid         : LEVEL strain
    LEVEL       : /[1-7]/
 
    // ?strain = inlining (pas de nœud intermédiaire dans l'arbre)
    ?strain     : suit_strain | nt_strain
    suit_strain : SUIT_TOKEN
    nt_strain   : NT_TOKEN
    SUIT_TOKEN  : "C" | "D" | "H" | "S"      // couleurs (anglais)
                | "T" | "K" | "Ca" | "Co"     // alias français (Trèfle/Carreau)
    NT_TOKEN    : "NT" | "SA" | "N"           // No Trump / Sans Atout
 
    // Annonces spéciales — priorités descendantes pour éviter X ⊂ XX
    special_call : RDBL | DBL | PASS
    RDBL.3      : "XX"                        // Surcontre  — priorité 3
    DBL.2       : "X"                         // Contre     — priorité 2
    PASS.2      : "PASS" | "Pass" | "passe" | "P"
 
    // ── Direction ────────────────────────────────────────────────────────────
    direction   : DIR_TOKEN
    DIR_TOKEN   : "N" | "E" | "S" | "W"
                | "Nord" | "Est" | "Sud" | "Ouest"   // alias français
 
    // ── Vulnérabilité ─────────────────────────────────────────────────────────
    vul         : VUL_TOKEN
    VUL_TOKEN   : "None" | "Love" | "Personne"
                | "N-S"  | "NS"
                | "E-W"  | "EW"
                | "All"  | "Both" | "Tous"
 
    // ── Carte individuelle (hors distribution) ────────────────────────────────
    card        : RANK_TOKEN SUIT_TOKEN
    RANK_TOKEN  : /[AKQJT98765432]/
 
    // ── Tokens génériques ─────────────────────────────────────────────────────
    NUMBER      : /[0-9]+/
    %ignore /[ \t\n\r]+/
"""
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  TABLES DE CORRESPONDANCE  (tokens → enum bridgebots)
# ═══════════════════════════════════════════════════════════════════════════════
 
_SUIT_MAP: dict[str, Suit] = {
    "C": Suit.CLUBS,    "T": Suit.CLUBS,    "Ca": Suit.CLUBS,
    "D": Suit.DIAMONDS, "K": Suit.DIAMONDS, "Co": Suit.DIAMONDS,
    "H": Suit.HEARTS,
    "S": Suit.SPADES,
}
 
_DIR_MAP: dict[str, Direction] = {
    "N": Direction.NORTH, "Nord":  Direction.NORTH,
    "E": Direction.EAST,  "Est":   Direction.EAST,
    "S": Direction.SOUTH, "Sud":   Direction.SOUTH,
    "W": Direction.WEST,  "Ouest": Direction.WEST,
}
 
_RANK_MAP: dict[str, Rank] = {
    "2": Rank.TWO,  "3": Rank.THREE, "4": Rank.FOUR, "5": Rank.FIVE,
    "6": Rank.SIX,  "7": Rank.SEVEN, "8": Rank.EIGHT,"9": Rank.NINE,
    "T": Rank.TEN,  "J": Rank.JACK,  "Q": Rank.QUEEN,"K": Rank.KING,
    "A": Rank.ACE,
}
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  TRANSFORMATEUR  (arbre Lark → objets bridgebots)
# ═══════════════════════════════════════════════════════════════════════════════
 
class BridgeTransformer(Transformer):
    """
    Visite l'arbre de parse Lark et retourne des objets bridgebots.
 
    Règles de nommage Lark :
      - La méthode  def foo(self, items)  traite la règle « foo ».
      - @v_args(inline=True) passe chaque item comme argument positionnel.
    """
 
    # ── Tokens simples ────────────────────────────────────────────────────────
 
    def NUMBER(self, tok: Token) -> int:
        return int(tok)
 
    def LEVEL(self, tok: Token) -> int:
        return int(tok)
 
    def SUIT_TOKEN(self, tok: Token) -> Suit:
        return _SUIT_MAP[str(tok)]
 
    def DIR_TOKEN(self, tok: Token) -> Direction:
        return _DIR_MAP[str(tok)]
 
    def RANK_TOKEN(self, tok: Token) -> Rank:
        return _RANK_MAP[str(tok).upper()]
 
    def CARD_CHAR(self, tok: Token) -> str:
        return str(tok)
 
    def VUL_TOKEN(self, tok: Token) -> str:
        return str(tok)
 
    def NT_TOKEN(self, tok: Token) -> None:
        return None              # suit=None signifie Sans-Atout dans bridgebots
 
    def EXPL_TEXT(self, tok: Token) -> str:
        return str(tok).strip()
 
    # ── Direction / vulnérabilité ─────────────────────────────────────────────
 
    @v_args(inline=True)
    def direction(self, dir_tok: Direction) -> Direction:
        return dir_tok
 
    @v_args(inline=True)
    def vul(self, vul_tok: str) -> str:
        return vul_tok
 
    # ── Couleur dans l'enchère ────────────────────────────────────────────────
 
    @v_args(inline=True)
    def suit_strain(self, suit: Suit) -> Suit:
        return suit
 
    @v_args(inline=True)
    def nt_strain(self, _nt) -> None:
        return None              # Sans-Atout
 
    # ── Enchère normale ───────────────────────────────────────────────────────
 
    @v_args(inline=True)
    def bid(self, level: int, strain) -> Bid:
        """
        Retourne un Bid bridgebots : Bid(level=n, suit=Suit.XXX | None)
        None pour le Sans-Atout, conformément à la convention bridgebots.
        """
        return Bid(level=level, suit=strain)
 
    # ── Annonces spéciales ────────────────────────────────────────────────────
 
    @v_args(inline=True)
    def special_call(self, token: Token) -> Bid:
        """PASS → Bid(0, None, 'PASS')  /  X → Bid(0, None, 'X')  /  XX → …"""
        val = str(token)
        if val in ("PASS", "Pass", "passe", "P"):
            return Bid(level=0, suit=None, call="PASS")
        if val == "X":
            return Bid(level=0, suit=None, call="X")
        if val == "XX":
            return Bid(level=0, suit=None, call="XX")
 
    # ── Annotations ──────────────────────────────────────────────────────────
 
    def alert(self, _items) -> BidAnnotation:
        return BidAnnotation(alert=True)
 
    def no_alert(self, _items) -> BidAnnotation:
        return BidAnnotation(alert=False)
 
    @v_args(inline=True)
    def explanation(self, text: str) -> BidAnnotation:
        return BidAnnotation(alert=True, explanation=text)
 
    # ── Appel annoté ─────────────────────────────────────────────────────────
 
    def annotated_call(self, items) -> Tuple[Bid, Optional[BidAnnotation]]:
        bid_obj = items[0]
        annotation = items[1] if len(items) > 1 else None
        return (bid_obj, annotation)
 
    # ── Séquence d'enchères ──────────────────────────────────────────────────
 
    def auction(self, items: list) -> List[Tuple[Bid, Optional[BidAnnotation]]]:
        return items    # list de (Bid, BidAnnotation|None)
 
    # ── Distribution PBN ─────────────────────────────────────────────────────
 
    def pbn_suit(self, items) -> List[str]:
        return [str(c) for c in items]
 
    def pbn_hand(self, items) -> dict:
        """Retourne {Suit: [cartes]} dans l'ordre S.H.D.C (PBN)"""
        spades, hearts, diamonds, clubs = items
        return {
            Suit.SPADES:   spades,
            Suit.HEARTS:   hearts,
            Suit.DIAMONDS: diamonds,
            Suit.CLUBS:    clubs,
        }
 
    @v_args(inline=True)
    def pbn_deal(self, first_dir: Direction, *hands) -> dict:
        """
        Distribue les 4 mains dans l'ordre N/E/S/W à partir de first_dir.
        Retourne {Direction: {Suit: [str]}}
        """
        order = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
        start = order.index(first_dir)
        rotated = order[start:] + order[:start]
        return {d: h for d, h in zip(rotated, hands)}
 
    # ── Balises PBN ──────────────────────────────────────────────────────────
 
    @v_args(inline=True)
    def board_tag(self, num: int) -> int:
        return num
 
    @v_args(inline=True)
    def dealer_tag(self, d: Direction) -> Direction:
        return d
 
    @v_args(inline=True)
    def vul_tag(self, v: str) -> str:
        return v
 
    @v_args(inline=True)
    def deal_tag(self, deal: dict) -> dict:
        return deal
 
    @v_args(inline=True)
    def auction_tag(self, dealer: Direction, auction: list) -> Tuple[Direction, list]:
        return (dealer, auction)
 
    # ── Carte individuelle ────────────────────────────────────────────────────
 
    @v_args(inline=True)
    def card(self, rank: Rank, suit: Suit) -> Card:
        return Card(rank=rank, suit=suit)
 
    # ── Donne complète ────────────────────────────────────────────────────────
 
    def board_record(self, items) -> BoardRecord:
        board_num   = items[0]           # board_tag
        dealer      = items[1]           # dealer_tag
        vul         = items[2]           # vul_tag
        hands       = items[3]           # deal_tag
        dealer2, auction_calls = items[4]  # auction_tag
 
        bid_record = BidRecord(
            dealer=dealer,
            bids=auction_calls,
        )
        return BoardRecord(
            board_num=board_num,
            dealer=dealer,
            vulnerable=vul,
            hands=hands,
            bid_record=bid_record,
        )
 
    def start(self, items: list) -> List[BoardRecord]:
        return items
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTRUCTEUR DU PARSEUR
# ═══════════════════════════════════════════════════════════════════════════════
 
def build_parser(start: str = "start") -> Lark:
    """
    Construit et retourne un parseur Lark LALR avec lexer contextuel.
 
    Le lexer contextuel (défaut LALR) résout les ambiguïtés :
      - 'N' en position direction  → DIR_TOKEN
      - 'NT'/'SA' en position couleur → NT_TOKEN
      - 'X'  → DBL,  'XX' → RDBL  (grâce aux priorités .2 / .3)
    """
    return Lark(
        BRIDGE_GRAMMAR,
        parser="lalr",
        start=start,
        propagate_positions=False,
    )
 
 
def parse_auction_only(text: str) -> List[Tuple[Bid, Optional[BidAnnotation]]]:
    """
    Raccourci : parse une séquence d'enchères seule (sans balises PBN).
 
    Exemple :
        parse_auction_only("1C! {Naturelle} 1H 2C PASS X PASS PASS PASS")
    """
    parser = Lark(BRIDGE_GRAMMAR, parser="lalr", start="auction")
    tree   = parser.parse(text)
    return BridgeTransformer().transform(tree)
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  DONNÉES D'EXEMPLE
# ═══════════════════════════════════════════════════════════════════════════════
 
EXEMPLE_PBN = """\
[Board 7]
[Dealer N]
[Vulnerable N-S]
[Deal N:AKQ3.JT9.876.432 T98.AKQ.AKQJ.KQJ 7654.8765.432.AT9 J2.432.T95.8765]
[Auction N]
1NT PASS 2C! {Stayman} 2H
PASS 4H PASS PASS
PASS
"""
 
EXEMPLE_SEQUENCE = "1C! {Mineure forcing} 1H 2C 3H 4C PASS PASS X PASS PASS PASS"
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  UTILITAIRES D'AFFICHAGE
# ═══════════════════════════════════════════════════════════════════════════════
 
def _fmt_bid(bid: Bid) -> str:
    if bid.call:
        return bid.call
    suit_str = (bid.suit.value if bid.suit else "SA")
    return f"{bid.level}{suit_str}"
 
 
def print_board(board: BoardRecord) -> None:
    print(f"\n{'─'*50}")
    print(f"  Donne #{board.board_num}  •  Donneur : {board.dealer.name}")
    print(f"  Vulnérabilité : {board.vulnerable}")
    print(f"  Distribution :")
    for dir_, hand in board.hands.items():
        for suit, cards in hand.items():
            print(f"    {dir_.name:5s} {suit.name:8s} : {''.join(cards) or '(chicane)'}")
    print(f"  Enchères (donneur = {board.bid_record.dealer.name}) :")
    for i, (bid, ann) in enumerate(board.bid_record.bids):
        ann_str = ""
        if ann:
            ann_str = "!" if ann.alert else ""
            if ann.explanation:
                ann_str += f" [{ann.explanation}]"
        print(f"    {i+1:2d}. {_fmt_bid(bid)}{ann_str}")
 
 
def print_auction(bids: list) -> None:
    print("\nSéquence d'enchères :")
    for i, (bid, ann) in enumerate(bids):
        ann_str = ""
        if ann:
            ann_str = "!" if ann.alert else ""
            if ann.explanation:
                ann_str += f" [{ann.explanation}]"
        print(f"  {i+1:2d}. {_fmt_bid(bid)}{ann_str}")
 
 
# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN — DÉMONSTRATION
# ═══════════════════════════════════════════════════════════════════════════════
 
if __name__ == "__main__":
    print("=" * 50)
    print(" Démonstration : Grammaire Lark × bridgebots")
    print("=" * 50)
 
    # ── 1. Parse d'une donne complète PBN ─────────────────────────────────────
    print("\n[1] Parse d'une donne PBN complète :")
    parser = build_parser()
    tree   = parser.parse(EXEMPLE_PBN)
    boards = BridgeTransformer().transform(tree)
    print_board(boards[0])
 
    # ── 2. Parse d'une séquence d'enchères seule ─────────────────────────────
    print("\n[2] Parse d'une séquence d'enchères seule :")
    bids = parse_auction_only(EXEMPLE_SEQUENCE)
    print_auction(bids)
 
    # ── 3. Affichage de l'arbre de parse brut ─────────────────────────────────
    print("\n[3] Arbre de parse (séquence courte '2H PASS X') :")
    p2   = Lark(BRIDGE_GRAMMAR, parser="lalr", start="auction")
    tree2 = p2.parse("2H PASS X")
    print(tree2.pretty())
 