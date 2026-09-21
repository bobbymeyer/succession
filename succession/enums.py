"""Core enumerations for Court of Succession.

Every attribute a courtier can carry, plus the six inner-circle seats.
String enums keep CSV/SQLite logging readable without conversion helpers.
"""

from __future__ import annotations

from enum import Enum


class Estate(str, Enum):
    MILITARY = "Military"
    CHURCH = "Church"
    MERCHANT = "Merchant"
    COMMONS = "Commons"


class Faith(str, Enum):
    OLD_GODS = "Old Gods"
    MYSTERY_CULTS = "Mystery Cults"
    ONE_GOD = "The One God"
    #: Actively godless. A real faith value a courtier can be born with or be
    #: pushed into by Apostasy -- distinct from NONE, which is the empty slot
    #: an Excommunication leaves behind.
    GODLESS = "Godless"
    NONE = "None"


class Family(str, Enum):
    AMONIDES = "Amonides"
    MITREAS = "Mitreas"
    ARGAIAN = "Argaian"
    NONE = "None"


class Origin(str, Enum):
    IMPERIAL = "Imperial"
    BARBARIAN = "Barbarian"


class People(str, Enum):
    """Flavour only: which barbarian people a courtier comes from."""

    EGYPTIAN = "Egyptian"
    PERSIAN = "Persian"
    SCYTHIAN = "Scythian"
    GERMAN = "German"
    NONE = "None"


class Seat(str, Enum):
    ARCHIEREUS = "Archiereus"
    ORACLE = "Oracle"
    STRATEGUS = "Strategus"
    SOMATOPHYLAX = "Somatophylax"
    DIOECETES = "Dioecetes"
    AGORANOMUS = "Agoranomus"
    DEMARCHUS = "Demarchus"


#: Only a courtier whose estate matches may occupy a seat. Church, Military
#: and Merchant each have a pair of mechanically identical seats; Commons has
#: one.
SEAT_ESTATE: dict[Seat, Estate] = {
    Seat.ARCHIEREUS: Estate.CHURCH,
    Seat.ORACLE: Estate.CHURCH,
    Seat.STRATEGUS: Estate.MILITARY,
    Seat.SOMATOPHYLAX: Estate.MILITARY,
    Seat.DIOECETES: Estate.MERCHANT,
    Seat.AGORANOMUS: Estate.MERCHANT,
    Seat.DEMARCHUS: Estate.COMMONS,
}

SEATS: tuple[Seat, ...] = tuple(SEAT_ESTATE)


#: The faiths an agenda can be built on. Godlessness deliberately has none: a
#: godless courtier in a seat is a seat no faith can count.
FAITHS: tuple[Faith, ...] = (Faith.OLD_GODS, Faith.MYSTERY_CULTS, Faith.ONE_GOD)
FAMILIES: tuple[Family, ...] = (Family.AMONIDES, Family.MITREAS, Family.ARGAIAN)


class CardKind(str, Enum):
    COURTIER = "Courtier"
    EVENT = "Event"
    OUTMANEUVER = "Outmaneuver"
    PROMOTION = "Promotion"
    DEMOTION = "Demotion"
    REMOVAL = "Removal"
    DEFENSE = "Defense"
    STRIP = "Strip"
    MUTATION = "Mutation"
    PIVOT = "Pivot"


#: Categories a Defense attachment negates (Events are explicitly excluded).
DEFENDABLE: frozenset[CardKind] = frozenset(
    {CardKind.REMOVAL, CardKind.DEMOTION, CardKind.STRIP, CardKind.MUTATION}
)
