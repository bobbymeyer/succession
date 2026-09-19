"""Game configuration, live courtier state, and the game state container.

`GameState` is designed to be cloned cheaply: every zone is a list/dict of
integer card uids, and `CourtierState` is frozen, so `clone()` is a handful of
shallow copies. The bots lean on this for one-ply lookahead.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional

from .cards import CardDef, build_cards
from .courtiers import COURTIERS_BY_NAME, CourtierDef
from .enums import SEAT_ESTATE, SEATS, Estate, Seat

ZONE_DECK = "deck"
ZONE_HAND = "hand"
ZONE_OUTER = "outer"
ZONE_INNER = "inner"
ZONE_DISCARD = "discard"
ZONE_REMOVED = "removed"


@dataclass(frozen=True, slots=True)
class Config:
    """Every rules knob that the source document left open or configurable."""

    #: Bot tier per seat, clockwise. Length sets the player count.
    players: tuple[str, ...] = ("naive", "greedy", "strategic", "naive")
    starting_hand: int = 5
    hand_limit: int = 7
    max_turns: int = 600
    #: Randomise which tier sits where, so seat order does not bias results.
    shuffle_seats: bool = True
    outmaneuver_copies: int = 1
    #: A d6 save succeeds on an even roll.
    save_on_even: bool = True
    #: Killed courtiers go to the discard and may reshuffle in as a *new*
    #: person with printed attributes. Set False to take them out of the game
    #: entirely (the stricter reading of the Removals text).
    removed_courtiers_return_to_deck: bool = True
    #: Require an estate-specific Defense to protect a courtier of that estate
    #: (the text only requires the *sacrificed* courtier to match).
    defense_requires_matching_target: bool = False
    #: Require one of a House Rising trio to sit in the family's own estate.
    house_rising_requires_preferred_seat: bool = True
    #: Inner seats a faith must hold for Faith Ascendant.
    faith_seats: int = 4
    #: Seats that must be filled before Balance counts.
    balance_seats: int = 7
    #: Barbarians Balance wants seated, not just one.
    balance_barbarians: int = 2
    #: Agenda keys left out of the pool entirely -- neither dealt nor available
    #: to a Schismatic Event. For asking what the game looks like without one.
    excluded_agendas: tuple[str, ...] = ()
    #: Overrides for a family's own estate, e.g. (("Mitreas", "Church"),).
    #: Unlisted families use courtiers.FAMILY_PREFERRED_ESTATE.
    house_preferred_estates: tuple[tuple[str, str], ...] = ()

    @property
    def num_players(self) -> int:
        return len(self.players)


@dataclass(frozen=True, slots=True)
class CourtierState:
    """A courtier's live attributes plus which of them have been mutated.

    Each attribute may be mutated at most once per courtier. Strips do *not*
    consume the mutation allowance, so a stripped attribute can be restored
    later by Conversion or Adoption.
    """

    estate: Estate
    faith: Faith
    family: Family
    origin: Origin
    mutated_estate: bool = False
    mutated_faith: bool = False
    mutated_family: bool = False
    mutated_origin: bool = False

    @classmethod
    def from_def(cls, d: CourtierDef) -> "CourtierState":
        return cls(d.estate, d.faith, d.family, d.origin)

    def mutated(self, attribute: str) -> bool:
        return bool(getattr(self, f"mutated_{attribute}"))

    def with_attribute(self, attribute: str, value, *, is_mutation: bool) -> "CourtierState":
        changes = {attribute: value}
        if is_mutation:
            changes[f"mutated_{attribute}"] = True
        return replace(self, **changes)


@dataclass
class GameState:
    config: Config
    cards: tuple[CardDef, ...]
    deck: list[int] = field(default_factory=list)
    discard: list[int] = field(default_factory=list)
    hands: list[list[int]] = field(default_factory=list)
    outer: list[int] = field(default_factory=list)
    seats: dict[Seat, Optional[int]] = field(default_factory=dict)
    removed: list[int] = field(default_factory=list)
    #: courtier uid -> defense card uid attached to them
    defenses: dict[int, int] = field(default_factory=dict)
    #: courtier card uid -> live attributes
    cstate: dict[int, CourtierState] = field(default_factory=dict)
    #: per-player agenda key; agendas stay private unless revealed
    agendas: list[str] = field(default_factory=list)
    unused_agendas: list[str] = field(default_factory=list)
    revealed: list[bool] = field(default_factory=list)
    skip_next: list[bool] = field(default_factory=list)
    current: int = 0
    turn: int = 0
    reshuffles: int = 0
    winners: list[int] = field(default_factory=list)
    #: Counters for the per-game log (cards played by kind, etc.).
    stats: dict[str, int] = field(default_factory=dict)
    #: Human-readable trace; only populated when `trace` is enabled.
    log: list[str] = field(default_factory=list)
    trace: bool = False

    # -- construction -------------------------------------------------------
    @classmethod
    def new(cls, config: Config) -> "GameState":
        cards = build_cards(config.outmaneuver_copies)
        state = cls(config=config, cards=cards)
        state.seats = {s: None for s in SEATS}
        state.hands = [[] for _ in range(config.num_players)]
        state.revealed = [False] * config.num_players
        state.skip_next = [False] * config.num_players
        state.cstate = {
            uid: CourtierState.from_def(COURTIERS_BY_NAME[c.courtier])
            for uid, c in enumerate(cards)
            if c.is_courtier
        }
        return state

    def clone(self) -> "GameState":
        """A cheap independent copy, used for bot lookahead."""

        return GameState(
            config=self.config,
            cards=self.cards,  # immutable, shared
            deck=list(self.deck),
            discard=list(self.discard),
            hands=[list(h) for h in self.hands],
            outer=list(self.outer),
            seats=dict(self.seats),
            removed=list(self.removed),
            defenses=dict(self.defenses),
            cstate=dict(self.cstate),  # values are frozen
            agendas=list(self.agendas),
            unused_agendas=list(self.unused_agendas),
            revealed=list(self.revealed),
            skip_next=list(self.skip_next),
            current=self.current,
            turn=self.turn,
            reshuffles=self.reshuffles,
            winners=list(self.winners),
            stats=dict(self.stats),
            log=[],
            trace=False,
        )

    # -- lookups ------------------------------------------------------------
    def card(self, uid: int) -> CardDef:
        return self.cards[uid]

    def name(self, uid: int) -> str:
        return self.cards[uid].name

    def base(self, uid: int) -> CourtierDef:
        return COURTIERS_BY_NAME[self.cards[uid].courtier]

    def seat_of(self, uid: int) -> Optional[Seat]:
        for seat, occupant in self.seats.items():
            if occupant == uid:
                return seat
        return None

    def occupied_seats(self) -> list[Seat]:
        return [s for s in SEATS if self.seats[s] is not None]

    def empty_seats(self) -> list[Seat]:
        return [s for s in SEATS if self.seats[s] is None]

    def inner_uids(self) -> list[int]:
        return [uid for uid in self.seats.values() if uid is not None]

    def inner_courtiers(self) -> list[CourtierState]:
        return [self.cstate[uid] for uid in self.seats.values() if uid is not None]

    def uids_in_play(self) -> list[int]:
        return self.inner_uids() + self.outer

    def courtiers_in_play(self) -> list[CourtierState]:
        return [self.cstate[uid] for uid in self.uids_in_play()]

    def is_inner(self, uid: int) -> bool:
        return self.seat_of(uid) is not None

    def seat_estate(self, seat: Seat) -> Estate:
        return SEAT_ESTATE[seat]

    def bump(self, key: str, amount: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + amount

    def note(self, message: str) -> None:
        if self.trace:
            self.log.append(f"[t{self.turn}] {message}")

    # -- board summary ------------------------------------------------------
    def board_summary(self) -> dict[str, str]:
        """Seat -> occupant epithet (empty string for a vacant seat)."""

        return {
            seat.value: (self.name(uid) if uid is not None else "")
            for seat, uid in self.seats.items()
        }

    def describe(self) -> str:
        lines = ["Inner circle:"]
        for seat in SEATS:
            uid = self.seats[seat]
            if uid is None:
                lines.append(f"  {seat.value:<24} --")
            else:
                c = self.cstate[uid]
                lines.append(
                    f"  {seat.value:<24} {self.name(uid)} "
                    f"({c.estate.value}/{c.faith.value}/{c.family.value}/{c.origin.value})"
                )
        lines.append(f"Outer circle ({len(self.outer)}): " + ", ".join(sorted(self.name(u) for u in self.outer)))
        return "\n".join(lines)
