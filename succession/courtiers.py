"""The 40-courtier table.

Every courtier is born into one of the three faiths but one: the Dog of the
Agora, a barefoot cynic who sleeps in a wine jar and carries a lamp through the
market at noon, looking for an honest man. He is the only Godless courtier on
the roster, and the reason the three faiths come out even at thirteen apiece.
Everyone else reaches godlessness the hard way, through Apostasy. Godlessness is a real faith value, not an absence:
it has no agenda of its own, so a godless courtier in an inner seat is a seat
neither faith can count. Only Old Gods and Mystery Cults need to be level with
each other -- the Godless need no win path, so they can be few.


Courtiers are identified by epithet only. A courtier killed during play may be
reshuffled back into the deck as a *new* person bearing the same reputation --
they re-enter with their printed (base) attributes, never with whatever
mutations or strips the dead one had accumulated.

`house` is thematic flavour (which house a courtier is drawn from); `family` is
the mechanical attribute agendas care about. For commoners and barbarians the
two coincide as "no family".
"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import Estate, Faith, Family, Origin, People


@dataclass(frozen=True, slots=True)
class CourtierDef:
    """Printed (base) attributes of one courtier card."""

    name: str
    estate: Estate
    faith: Faith
    family: Family
    origin: Origin
    people: People = People.NONE

    @property
    def house(self) -> str:
        if self.family is not Family.NONE:
            return self.family.value
        return "Barbarian" if self.origin is Origin.BARBARIAN else "Commoner"


_E, _C, _M, _K = Estate.MILITARY, Estate.CHURCH, Estate.MERCHANT, Estate.COMMONS
_OG, _MC = Faith.OLD_GODS, Faith.MYSTERY_CULTS
_1G, _GL = Faith.ONE_GOD, Faith.GODLESS
_AM, _MI, _AR, _NF = Family.AMONIDES, Family.MITREAS, Family.ARGAIAN, Family.NONE
_IMP, _BAR = Origin.IMPERIAL, Origin.BARBARIAN


COURTIERS: tuple[CourtierDef, ...] = (
    # --- House Amonides (Old Gods, Church-affiliated) -----------------------
    # Each house fields a third courtier in its own estate -- the seventh name
    # in each list -- so it can reach its House Rising seat without spending
    # both of its estate courtiers, and a charioteer, its one commoner, which
    # is the only way a house can ever hold the Demarchus's seat.
    CourtierDef("Beloved of the Gods", _C, _OG, _AM, _IMP),
    CourtierDef("Keeper of the Long Peace", _E, _OG, _AM, _IMP),
    CourtierDef("Hand of the Oracle", _C, _OG, _AM, _IMP),
    CourtierDef("Weigher of Grain", _M, _OG, _AM, _IMP),
    CourtierDef("Speaker of the Old Words", _E, _OG, _AM, _IMP),
    CourtierDef("Wearer of the Golden Diadem", _M, _OG, _AM, _IMP),
    CourtierDef("Tender of the Ancestral Flame", _C, _OG, _AM, _IMP),
    CourtierDef("Charioteer of the Sun Team", _K, _OG, _AM, _IMP),
    # --- House Mitreas (Mystery Cults, Merchant-affiliated) -----------------
    CourtierDef("Golden Thumb", _M, _MC, _MI, _IMP),
    CourtierDef("Initiate of the Seven Veils", _C, _MC, _MI, _IMP),
    CourtierDef("Crosser of Rivers", _E, _MC, _MI, _IMP),
    CourtierDef("Buyer of Cities", _M, _MC, _MI, _IMP),
    CourtierDef("Whisperer to the Serpent", _C, _MC, _MI, _IMP),
    CourtierDef("Rider of the Long Road", _E, _MC, _MI, _IMP),
    CourtierDef("Creditor of Kings", _M, _MC, _MI, _IMP),
    CourtierDef("Charioteer of the Seven Turns", _K, _MC, _MI, _IMP),
    # --- House Argaian (mixed faith, Military-affiliated) -------------------
    CourtierDef("Horse Breaker", _E, _MC, _AR, _IMP),
    CourtierDef("Destroyer of Walls", _E, _OG, _AR, _IMP),
    CourtierDef("Reader of Omens", _C, _1G, _AR, _IMP),
    CourtierDef("Sword of the Assembly", _C, _1G, _AR, _IMP),
    CourtierDef("Founder of Markets", _M, _1G, _AR, _IMP),
    CourtierDef("Uncrowned Victor", _M, _OG, _AR, _IMP),
    CourtierDef("Taker of the Citadel", _E, _1G, _AR, _IMP),
    CourtierDef("Charioteer of the Iron Wheel", _K, _1G, _AR, _IMP),
    # --- Commoners (unaffiliated, Imperial) ---------------------------------
    CourtierDef("Silver Tongue", _K, _1G, _NF, _IMP),
    CourtierDef("The Dog of the Agora", _K, _GL, _NF, _IMP),
    CourtierDef("Mender of Bones", _K, _MC, _NF, _IMP),
    CourtierDef("Ten Thousand Verses", _K, _OG, _NF, _IMP),
    CourtierDef("Builder of the Long Aqueduct", _K, _1G, _NF, _IMP),
    CourtierDef("Risen from the Ranks", _E, _1G, _NF, _IMP),
    CourtierDef("Coin-Counter of the Assembly", _M, _1G, _NF, _IMP),
    CourtierDef("Widow of the Temple", _C, _1G, _NF, _IMP),
    # --- Barbarians (unaffiliated, Barbarian origin, two per people) --------
    CourtierDef("Priest of the Two-Horned God", _C, _MC, _NF, _BAR, People.EGYPTIAN),
    CourtierDef("Master Mason", _K, _MC, _NF, _BAR, People.EGYPTIAN),
    CourtierDef("Cataphract of the Iron Bridge", _E, _1G, _NF, _BAR, People.PERSIAN),
    CourtierDef("Caravan-Lord of the Salt Road", _M, _1G, _NF, _BAR, People.PERSIAN),
    CourtierDef("Hundred-Kill Rider", _E, _1G, _NF, _BAR, People.SCYTHIAN),
    CourtierDef("Blade for Any Banner", _E, _MC, _NF, _BAR, People.SCYTHIAN),
    CourtierDef("Warlord of the Iron Grove", _E, _OG, _NF, _BAR, People.GERMAN),
    CourtierDef("Master Swordsmith", _K, _OG, _NF, _BAR, People.GERMAN),
)

COURTIERS_BY_NAME: dict[str, CourtierDef] = {c.name: c for c in COURTIERS}

#: Each house's affiliated estate, from the source document. House Rising asks
#: for one of its three seats here. Every family fields two courtiers in each
#: of Church, Military and Merchant, and each of those estates seats a pair, so
#: no house is short of candidates for its own estate.
FAMILY_PREFERRED_ESTATE: dict[Family, Estate] = {
    Family.AMONIDES: Estate.CHURCH,
    Family.MITREAS: Estate.MERCHANT,
    Family.ARGAIAN: Estate.MILITARY,
}
