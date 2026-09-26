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

from .courtiers import FAMILY_PREFERRED_ESTATE
from .enums import FAITHS, FAMILIES, SEAT_ESTATE, Faith, Family, Origin

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
    Agenda("faith_one_god", "Faith Ascendant: The One God", FAITH_ASCENDANT, Faith.ONE_GOD.value),
    Agenda("barbarian_conquest", "Barbarian Conquest", CONQUEST),
    Agenda("balance", "Balance", BALANCE),
)

AGENDA_KEYS: tuple[str, ...] = tuple(a.key for a in AGENDAS)
AGENDAS_BY_KEY: dict[str, Agenda] = {a.key: a for a in AGENDAS}

#: House Rising needs this many of the inner seats...
HOUSE_SEATS = 3
#: ...of which this many must sit in the family's own estate.
HOUSE_PREFERRED_SEATS = 1
#: Faith Ascendant needs this many of the inner seats. Four of seven is a bare
#: majority; five is the two-thirds the rule meant when the board had six.
FAITH_SEATS = 4
#: Balance must hold across this many of the seven seats. It was six, with two
#: barbarians; asking for one barbarian made Balance too easy, and asking for
#: every seat as well brings it back to an even share.
BALANCE_SEATS = 7
#: Barbarian Conquest: this many barbarians seated in the inner circle.
CONQUEST_BARBARIANS = 3
#: Balance wants this many barbarians seated. It was two; with events played
#: when drawn and the hand limit checked at the end of the turn, two left
#: Balance the weakest agenda by four points.
BALANCE_BARBARIANS = 1

@dataclass(frozen=True, slots=True)
class AgendaRules:
    """The agenda variants; see docs/RULES.md."""

    #: One of the three House Rising seats must be in the family's own estate.
    house_preferred_seat: bool = True
    #: Seats a faith must hold to win.
    faith_seats: int = FAITH_SEATS
    #: Seats that must be filled for Balance to count.
    balance_seats: int = BALANCE_SEATS
    #: Barbarians Balance wants seated.
    balance_barbarians: int = BALANCE_BARBARIANS
    #: Overrides layered on FAMILY_PREFERRED_ESTATE, as (family, estate) pairs.
    house_preferred_estate: tuple[tuple[str, str], ...] = ()

    def preferred_estate(self, family: str) -> str | None:
        for name, estate in self.house_preferred_estate:
            if name == family:
                return estate
        default = FAMILY_PREFERRED_ESTATE.get(Family(family))
        return default.value if default is not None else None


DEFAULT_RULES = AgendaRules()


def rules_for(state: "GameState") -> AgendaRules:
    config = state.config
    return AgendaRules(
        house_preferred_seat=config.house_rising_requires_preferred_seat,
        house_preferred_estate=config.house_preferred_estates,
        faith_seats=config.faith_seats,
        balance_seats=config.balance_seats,
        balance_barbarians=config.balance_barbarians,
    )


@dataclass(frozen=True, slots=True)
class BoardCounts:
    """One pass over the board, enough to judge all seven agendas."""

    inner_family: dict[str, int]
    inner_faith: dict[str, int]
    outer_family: dict[str, int]
    outer_faith: dict[str, int]
    #: family -> seat estate -> seats held, for House Rising's estate pair
    inner_family_estate: dict[str, dict[str, int]]
    inner_filled: int
    inner_barbarians: int
    barbarians_in_play: int


def count_board(state: "GameState") -> BoardCounts:
    inner_family: dict[str, int] = {}
    inner_faith: dict[str, int] = {}
    outer_family: dict[str, int] = {}
    outer_faith: dict[str, int] = {}
    inner_family_estate: dict[str, dict[str, int]] = {}
    inner_filled = 0
    inner_barbarians = 0
    barbarians = 0

    cstate = state.cstate
    for seat, uid in state.seats.items():
        if uid is None:
            continue
        c = cstate[uid]
        inner_filled += 1
        family = c.family.value
        inner_family[family] = inner_family.get(family, 0) + 1
        inner_faith[c.faith.value] = inner_faith.get(c.faith.value, 0) + 1
        # Keyed on the seat's estate, which is what "two seats in one estate"
        # means -- identical to the occupant's estate in any legal position.
        estates = inner_family_estate.setdefault(family, {})
        estate = SEAT_ESTATE[seat].value
        estates[estate] = estates.get(estate, 0) + 1
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
        inner_filled,
        inner_barbarians,
        barbarians,
    )


def _preferred_seats(counts: BoardCounts, family: str, rules: AgendaRules) -> int:
    """Seats this family holds in its own estate."""

    estates = counts.inner_family_estate.get(family)
    preferred = rules.preferred_estate(family)
    if not estates or preferred is None:
        return 0
    return estates.get(preferred, 0)


def satisfied_counts(
    counts: BoardCounts, agenda: Agenda, rules: AgendaRules = DEFAULT_RULES
) -> bool:
    kind = agenda.kind
    if kind == HOUSE_RISING:
        if counts.inner_family.get(agenda.param, 0) < HOUSE_SEATS:
            return False
        if rules.house_preferred_seat:
            return _preferred_seats(counts, agenda.param, rules) >= HOUSE_PREFERRED_SEATS
        return True
    if kind == FAITH_ASCENDANT:
        return counts.inner_faith.get(agenda.param, 0) >= rules.faith_seats
    if kind == CONQUEST:
        return counts.inner_barbarians >= CONQUEST_BARBARIANS
    if kind == BALANCE:
        return (
            counts.inner_filled >= rules.balance_seats
            and all(counts.inner_family.get(f.value, 0) > 0 for f in FAMILIES)
            and all(counts.inner_faith.get(f.value, 0) > 0 for f in FAITHS)
            and counts.inner_barbarians >= rules.balance_barbarians
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
        if rules.house_preferred_seat:
            held = min(_preferred_seats(counts, agenda.param, rules), HOUSE_PREFERRED_SEATS)
            core = 0.75 * core + 0.25 * held / HOUSE_PREFERRED_SEATS
        bench = min(counts.outer_family.get(agenda.param, 0), HOUSE_SEATS) / HOUSE_SEATS
    elif kind == FAITH_ASCENDANT:
        needed = rules.faith_seats
        core = counts.inner_faith.get(agenda.param, 0) / needed
        bench = min(counts.outer_faith.get(agenda.param, 0), needed) / needed
    elif kind == CONQUEST:
        core = min(counts.inner_barbarians, CONQUEST_BARBARIANS) / CONQUEST_BARBARIANS
        # Barbarians waiting outside are the raw material the bloc needs.
        bench = min(counts.barbarians_in_play - counts.inner_barbarians, 3) / 3
    elif kind == BALANCE:
        met = sum(1 for f in FAMILIES if counts.inner_family.get(f.value, 0) > 0)
        met += sum(1 for f in FAITHS if counts.inner_faith.get(f.value, 0) > 0)
        met += min(counts.inner_barbarians, rules.balance_barbarians)
        wanted = len(FAMILIES) + len(FAITHS) + rules.balance_barbarians
        seats = min(counts.inner_filled, rules.balance_seats) / rules.balance_seats
        core = 0.8 * met / wanted + 0.2 * seats
        bench = 0.0
    else:  # pragma: no cover
        raise ValueError(f"unknown agenda kind: {kind}")

    # Capped strictly below 1.0: an unsatisfied agenda never ties a won one.
    return min(0.98, 0.85 * core + 0.15 * bench)


@dataclass(frozen=True, slots=True)
class Condition:
    """One clause of an agenda, as it stands on the board.

    `waiting` counts courtiers in the outer circle who would help, when that
    means anything -- they are one move or one promotion from a seat.
    """

    label: str
    have: int
    need: int
    waiting: int | None = None

    @property
    def met(self) -> bool:
        return self.have >= self.need


def conditions(
    counts: BoardCounts, agenda: Agenda, rules: AgendaRules = DEFAULT_RULES
) -> list[Condition]:
    """The agenda clause by clause, for a player to see what is and isn't met.

    All of them met is exactly `satisfied_counts`; a test holds the two to it.
    """

    kind = agenda.kind
    if kind == HOUSE_RISING:
        family = agenda.param
        out = [
            Condition(
                f"House {family} holds {HOUSE_SEATS} seats",
                counts.inner_family.get(family, 0),
                HOUSE_SEATS,
                counts.outer_family.get(family, 0),
            )
        ]
        estate = rules.preferred_estate(family)
        if rules.house_preferred_seat and estate is not None:
            out.append(
                Condition(
                    f"{'One' if HOUSE_PREFERRED_SEATS == 1 else HOUSE_PREFERRED_SEATS} of them in a {estate} seat",
                    _preferred_seats(counts, family, rules),
                    HOUSE_PREFERRED_SEATS,
                )
            )
        return out
    if kind == FAITH_ASCENDANT:
        return [
            Condition(
                f"{agenda.param} hold {rules.faith_seats} seats",
                counts.inner_faith.get(agenda.param, 0),
                rules.faith_seats,
                counts.outer_faith.get(agenda.param, 0),
            )
        ]
    if kind == CONQUEST:
        return [
            Condition(
                f"{CONQUEST_BARBARIANS} barbarians seated",
                counts.inner_barbarians,
                CONQUEST_BARBARIANS,
                counts.barbarians_in_play - counts.inner_barbarians,
            )
        ]
    if kind == BALANCE:
        out = [Condition(f"{rules.balance_seats} of 7 seats filled", counts.inner_filled, rules.balance_seats)]
        out += [
            Condition(f"House {f.value} seated", counts.inner_family.get(f.value, 0), 1, counts.outer_family.get(f.value, 0))
            for f in FAMILIES
        ]
        out += [
            Condition(f"{f.value} seated", counts.inner_faith.get(f.value, 0), 1, counts.outer_faith.get(f.value, 0))
            for f in FAITHS
        ]
        out.append(
            Condition(
                f"{rules.balance_barbarians} barbarians seated",
                counts.inner_barbarians,
                rules.balance_barbarians,
                counts.barbarians_in_play - counts.inner_barbarians,
            )
        )
        return out
    raise ValueError(f"unknown agenda kind: {kind}")  # pragma: no cover


def contributors(state: "GameState", agenda: Agenda) -> list[int]:
    """The seated courtiers an agenda counts, in seat order.

    For a won agenda these are the courtiers who won it: the family's or the
    faith's seats, the barbarians, or, for Balance, the whole court.
    """

    cstate = state.cstate
    out = []
    for uid in state.seats.values():
        if uid is None:
            continue
        c = cstate[uid]
        kind = agenda.kind
        if (
            (kind == HOUSE_RISING and c.family.value == agenda.param)
            or (kind == FAITH_ASCENDANT and c.faith.value == agenda.param)
            or (kind == CONQUEST and c.origin is Origin.BARBARIAN)
            or kind == BALANCE
        ):
            out.append(uid)
    return out


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
