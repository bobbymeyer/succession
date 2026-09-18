"""The seven active agendas, their win conditions, and a progress metric.

`satisfied()` is the rule: the board predicate that lets a player reveal and
win. `progress()` is a bot-facing heuristic in [0, 1] -- 1.0 exactly when the
agenda is satisfied, partial credit for a board that is close -- and it is what
the greedy and strategic bots hill-climb on.

Both are computed from a single `BoardCounts` pass over the board, because the
bots evaluate every agenda against every candidate action and that inner loop
is the simulator's hot path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .enums import FAITHS, FAMILIES, MILITARY_SEATS, Faith, Family, Origin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .state import GameState

HOUSE_RISING = "house"
FAITH_ASCENDANT = "faith"
CONQUEST = "conquest"
BALANCE = "balance"


@dataclass(frozen=True, slots=True)
class Agenda:
    key: str
    name: str
    kind: str
    param: str = ""


AGENDAS: tuple[Agenda, ...] = (
    Agenda("house_amonides", "House Rising: Amonides", HOUSE_RISING, Family.AMONIDES.value),
    Agenda("house_mitreas", "House Rising: Mitreas", HOUSE_RISING, Family.MITREAS.value),
    Agenda("house_argaian", "House Rising: Argaian", HOUSE_RISING, Family.ARGAIAN.value),
    Agenda("faith_old_gods", "Faith Ascendant: Old Gods", FAITH_ASCENDANT, Faith.OLD_GODS.value),
    Agenda("faith_mystery_cults", "Faith Ascendant: Mystery Cults", FAITH_ASCENDANT, Faith.MYSTERY_CULTS.value),
    Agenda("conquest", "Conquest", CONQUEST),
    Agenda("balance", "Balance", BALANCE),
)

AGENDA_KEYS: tuple[str, ...] = tuple(a.key for a in AGENDAS)
AGENDAS_BY_KEY: dict[str, Agenda] = {a.key: a for a in AGENDAS}

#: House Rising / Faith Ascendant need this many of the six inner seats.
DOMINANCE_SEATS = 4
#: Conquest needs this many barbarians anywhere in play.
CONQUEST_BARBARIANS = 3


@dataclass(frozen=True, slots=True)
class BoardCounts:
    """One pass over the board, enough to judge all seven agendas."""

    inner_family: dict[str, int]
    inner_faith: dict[str, int]
    outer_family: dict[str, int]
    outer_faith: dict[str, int]
    inner_barbarians: int
    barbarians_in_play: int
    military_seats_filled: int
    military_seats_barbarian: int


def count_board(state: "GameState") -> BoardCounts:
    inner_family: dict[str, int] = {}
    inner_faith: dict[str, int] = {}
    outer_family: dict[str, int] = {}
    outer_faith: dict[str, int] = {}
    inner_barbarians = 0
    barbarians = 0
    military_filled = 0
    military_barbarian = 0

    cstate = state.cstate
    for seat in MILITARY_SEATS:
        uid = state.seats[seat]
        if uid is not None:
            military_filled += 1
            if cstate[uid].origin is Origin.BARBARIAN:
                military_barbarian += 1

    for uid in state.seats.values():
        if uid is None:
            continue
        c = cstate[uid]
        inner_family[c.family.value] = inner_family.get(c.family.value, 0) + 1
        inner_faith[c.faith.value] = inner_faith.get(c.faith.value, 0) + 1
        if c.origin is Origin.BARBARIAN:
            inner_barbarians += 1
            barbarians += 1

    for uid in state.outer:
        c = cstate[uid]
        outer_family[c.family.value] = outer_family.get(c.family.value, 0) + 1
        outer_faith[c.faith.value] = outer_faith.get(c.faith.value, 0) + 1
        if c.origin is Origin.BARBARIAN:
            barbarians += 1

    return BoardCounts(
        inner_family,
        inner_faith,
        outer_family,
        outer_faith,
        inner_barbarians,
        barbarians,
        military_filled,
        military_barbarian,
    )


def satisfied_counts(counts: BoardCounts, agenda: Agenda, *, strict_conquest: bool = False) -> bool:
    kind = agenda.kind
    if kind == HOUSE_RISING:
        return counts.inner_family.get(agenda.param, 0) >= DOMINANCE_SEATS
    if kind == FAITH_ASCENDANT:
        return counts.inner_faith.get(agenda.param, 0) >= DOMINANCE_SEATS
    if kind == CONQUEST:
        generals = (
            counts.military_seats_barbarian if strict_conquest else counts.military_seats_filled
        )
        return (
            counts.barbarians_in_play >= CONQUEST_BARBARIANS
            and generals >= len(MILITARY_SEATS)
        )
    if kind == BALANCE:
        return (
            all(counts.inner_family.get(f.value, 0) > 0 for f in FAMILIES)
            and all(counts.inner_faith.get(f.value, 0) > 0 for f in FAITHS)
            and counts.inner_barbarians > 0
        )
    raise ValueError(f"unknown agenda kind: {kind}")  # pragma: no cover


def progress_counts(counts: BoardCounts, agenda: Agenda, *, strict_conquest: bool = False) -> float:
    """Heuristic completion in [0, 1]; 1.0 iff satisfied.

    Courtiers waiting in the outer circle earn a little credit: they are one
    free move (or one promotion card) from a seat.
    """

    if satisfied_counts(counts, agenda, strict_conquest=strict_conquest):
        return 1.0

    kind = agenda.kind
    if kind == HOUSE_RISING:
        core = counts.inner_family.get(agenda.param, 0) / DOMINANCE_SEATS
        bench = min(counts.outer_family.get(agenda.param, 0), DOMINANCE_SEATS) / DOMINANCE_SEATS
    elif kind == FAITH_ASCENDANT:
        core = counts.inner_faith.get(agenda.param, 0) / DOMINANCE_SEATS
        bench = min(counts.outer_faith.get(agenda.param, 0), DOMINANCE_SEATS) / DOMINANCE_SEATS
    elif kind == CONQUEST:
        generals = (
            counts.military_seats_barbarian if strict_conquest else counts.military_seats_filled
        )
        core = 0.5 * min(counts.barbarians_in_play, CONQUEST_BARBARIANS) / CONQUEST_BARBARIANS
        core += 0.5 * generals / len(MILITARY_SEATS)
        bench = 0.0
    elif kind == BALANCE:
        met = sum(1 for f in FAMILIES if counts.inner_family.get(f.value, 0) > 0)
        met += sum(1 for f in FAITHS if counts.inner_faith.get(f.value, 0) > 0)
        met += 1 if counts.inner_barbarians else 0
        core = met / 6.0
        bench = 0.0
    else:  # pragma: no cover
        raise ValueError(f"unknown agenda kind: {kind}")

    # Capped strictly below 1.0: an unsatisfied agenda never ties a won one.
    return min(0.98, 0.85 * core + 0.15 * bench)


# --- state-level convenience wrappers --------------------------------------
def _strict(state: "GameState") -> bool:
    return state.config.conquest_requires_barbarian_generals


def satisfied(state: "GameState", agenda: Agenda) -> bool:
    return satisfied_counts(count_board(state), agenda, strict_conquest=_strict(state))


def progress(state: "GameState", agenda: Agenda) -> float:
    return progress_counts(count_board(state), agenda, strict_conquest=_strict(state))


def progress_vector(state: "GameState") -> dict[str, float]:
    """Progress of every agenda in the pool -- the strategic bot's threat radar."""

    counts = count_board(state)
    strict = _strict(state)
    return {a.key: progress_counts(counts, a, strict_conquest=strict) for a in AGENDAS}
