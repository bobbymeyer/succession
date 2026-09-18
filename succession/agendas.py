"""The seven active agendas, their win conditions, and a progress metric.

`satisfied_counts()` is the rule: the board predicate that lets a player reveal
and win. `progress_counts()` is a bot-facing heuristic in [0, 1] -- 1.0 exactly
when the agenda is satisfied, partial credit for a board that is close -- and
it is what the greedy and strategic bots hill-climb on.

Both read a single `BoardCounts` pass over the board, because the bots evaluate
every agenda against every candidate action and that is the simulator's hot
path.
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

#: House Rising needs this many of the six inner seats.
HOUSE_SEATS = 3
#: Faith Ascendant needs this many of the six inner seats.
FAITH_SEATS = 4
#: Conquest needs this many barbarians *in the inner circle*.
CONQUEST_BARBARIANS = 3
#: The strict House Rising variant wants this many seats of one estate.
HOUSE_ESTATE_PAIR = 2


@dataclass(frozen=True, slots=True)
class AgendaRules:
    """The agenda variants the brief left open; see docs/RULES.md."""

    #: Conquest's two Military seats must be held *by barbarians*.
    strict_conquest: bool = False
    #: A House Rising trio must include two seats of a single estate.
    house_estate_pair: bool = False


DEFAULT_RULES = AgendaRules()


def rules_for(state: "GameState") -> AgendaRules:
    config = state.config
    return AgendaRules(
        strict_conquest=config.conquest_requires_barbarian_generals,
        house_estate_pair=config.house_rising_requires_estate_pair,
    )


@dataclass(frozen=True, slots=True)
class BoardCounts:
    """One pass over the board, enough to judge all seven agendas."""

    inner_family: dict[str, int]
    inner_faith: dict[str, int]
    outer_family: dict[str, int]
    outer_faith: dict[str, int]
    #: family -> estate -> seats held, for the estate-pair House Rising variant
    inner_family_estate: dict[str, dict[str, int]]
    inner_barbarians: int
    barbarians_in_play: int
    military_seats_filled: int
    military_seats_barbarian: int


def count_board(state: "GameState") -> BoardCounts:
    inner_family: dict[str, int] = {}
    inner_faith: dict[str, int] = {}
    outer_family: dict[str, int] = {}
    outer_faith: dict[str, int] = {}
    inner_family_estate: dict[str, dict[str, int]] = {}
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
        family = c.family.value
        inner_family[family] = inner_family.get(family, 0) + 1
        inner_faith[c.faith.value] = inner_faith.get(c.faith.value, 0) + 1
        estates = inner_family_estate.setdefault(family, {})
        estates[c.estate.value] = estates.get(c.estate.value, 0) + 1
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
        inner_family_estate,
        inner_barbarians,
        barbarians,
        military_filled,
        military_barbarian,
    )


def _best_estate_block(counts: BoardCounts, family: str) -> int:
    """How many seats of a single estate this family holds."""

    estates = counts.inner_family_estate.get(family)
    return max(estates.values()) if estates else 0


def satisfied_counts(
    counts: BoardCounts, agenda: Agenda, rules: AgendaRules = DEFAULT_RULES
) -> bool:
    kind = agenda.kind
    if kind == HOUSE_RISING:
        if counts.inner_family.get(agenda.param, 0) < HOUSE_SEATS:
            return False
        if rules.house_estate_pair:
            return _best_estate_block(counts, agenda.param) >= HOUSE_ESTATE_PAIR
        return True
    if kind == FAITH_ASCENDANT:
        return counts.inner_faith.get(agenda.param, 0) >= FAITH_SEATS
    if kind == CONQUEST:
        generals = (
            counts.military_seats_barbarian
            if rules.strict_conquest
            else counts.military_seats_filled
        )
        return (
            counts.inner_barbarians >= CONQUEST_BARBARIANS
            and generals >= len(MILITARY_SEATS)
        )
    if kind == BALANCE:
        return (
            all(counts.inner_family.get(f.value, 0) > 0 for f in FAMILIES)
            and all(counts.inner_faith.get(f.value, 0) > 0 for f in FAITHS)
            and counts.inner_barbarians > 0
        )
    raise ValueError(f"unknown agenda kind: {kind}")  # pragma: no cover


def progress_counts(
    counts: BoardCounts, agenda: Agenda, rules: AgendaRules = DEFAULT_RULES
) -> float:
    """Heuristic completion in [0, 1]; 1.0 iff satisfied.

    Courtiers waiting in the outer circle earn a little credit: they are one
    free move (or one promotion card) from a seat.
    """

    if satisfied_counts(counts, agenda, rules):
        return 1.0

    kind = agenda.kind
    if kind == HOUSE_RISING:
        seated = counts.inner_family.get(agenda.param, 0)
        core = min(seated, HOUSE_SEATS) / HOUSE_SEATS
        if rules.house_estate_pair:
            block = min(_best_estate_block(counts, agenda.param), HOUSE_ESTATE_PAIR)
            core = 0.6 * core + 0.4 * block / HOUSE_ESTATE_PAIR
        bench = min(counts.outer_family.get(agenda.param, 0), HOUSE_SEATS) / HOUSE_SEATS
    elif kind == FAITH_ASCENDANT:
        core = counts.inner_faith.get(agenda.param, 0) / FAITH_SEATS
        bench = min(counts.outer_faith.get(agenda.param, 0), FAITH_SEATS) / FAITH_SEATS
    elif kind == CONQUEST:
        generals = (
            counts.military_seats_barbarian
            if rules.strict_conquest
            else counts.military_seats_filled
        )
        core = 0.5 * min(counts.inner_barbarians, CONQUEST_BARBARIANS) / CONQUEST_BARBARIANS
        core += 0.5 * generals / len(MILITARY_SEATS)
        # Barbarians waiting outside are the raw material Conquest needs.
        bench = min(counts.barbarians_in_play - counts.inner_barbarians, 3) / 3
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
def satisfied(state: "GameState", agenda: Agenda) -> bool:
    return satisfied_counts(count_board(state), agenda, rules_for(state))


def progress(state: "GameState", agenda: Agenda) -> float:
    return progress_counts(count_board(state), agenda, rules_for(state))


def progress_vector(state: "GameState") -> dict[str, float]:
    """Progress of every agenda in the pool -- the strategic bot's threat radar."""

    counts = count_board(state)
    rules = rules_for(state)
    return {a.key: progress_counts(counts, a, rules) for a in AGENDAS}
