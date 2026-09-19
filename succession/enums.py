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
    CHIEF_PRIEST = "Chief Priest"
    ORACLE = "Oracle"
    FIELD_GENERAL = "Field General"
    PRAETORIAN_CHIEF = "Praetorian Chief"
    EXCHEQUER = "Master of the Exchequer"
    HARBORMASTER = "Harbormaster"
    GUILDMASTER = "Guildmaster"


#: Only a courtier whose estate matches may occupy a seat. Church, Military
#: and Merchant each have a pair of mechanically identical seats; Commons has
#: one.
SEAT_ESTATE: dict[Seat, Estate] = {
    Seat.CHIEF_PRIEST: Estate.CHURCH,
    Seat.ORACLE: Estate.CHURCH,
    Seat.FIELD_GENERAL: Estate.MILITARY,
    Seat.PRAETORIAN_CHIEF: Estate.MILITARY,
    Seat.EXCHEQUER: Estate.MERCHANT,
    Seat.HARBORMASTER: Estate.MERCHANT,
    Seat.GUILDMASTER: Estate.COMMONS,
}

SEATS: tuple[Seat, ...] = tuple(SEAT_ESTATE)

#: Barbarian Conquest's "both generals" route reads these two seats.
MILITARY_SEATS: tuple[Seat, ...] = (Seat.FIELD_GENERAL, Seat.PRAETORIAN_CHIEF)

FAITHS: tuple[Faith, ...] = (Faith.OLD_GODS, Faith.MYSTERY_CULTS)
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
