"""Card definitions and deck construction.

The play deck is 84 cards: the 40 courtiers plus 44 action cards (10 events,
5 promotions, 5 demotions, 6 removals, 5 defenses, 2 strips, 9 mutations,
1 pivot, and N copies of Outmaneuver -- one by default).

Event effects are the one place where the source document could not be carried
over 1:1 (its effects were written for a board-wide version of events, while
the revised rule targets a single courtier). The `EVENT_EFFECTS` table below is
the single place to edit them; see docs/RULES.md for the open questions.
"""

from __future__ import annotations

from dataclasses import dataclass

from .courtiers import COURTIERS
from .enums import CardKind, Estate, Faith, Family, Origin

# --- Event effect primitives ------------------------------------------------
# Each event resolves to exactly one of these against its single target.
EFFECT_DEMOTE = "demote"                      # inner -> outer
EFFECT_REMOVE = "remove"                      # leaves play; may reshuffle back as a new person
EFFECT_ERASE = "erase"                        # leaves play and out of the game for good
EFFECT_RECALL = "recall"                      # leaves court, shuffled back into the deck
EFFECT_STRIP_FAITH = "strip_faith"            # faith -> None
EFFECT_STRIP_FAMILY = "strip_family"          # family -> None
EFFECT_RUIN = "ruin"                          # estate -> Commons, unseating them if it clashes
EFFECT_DEMOTE_AND_BREAK = "demote_and_break"  # demote and destroy any attached defense
EFFECT_BREAK_DEFENSE = "break_defense"        # destroy an attached defense
EFFECT_INSTALL = "install"                    # free install into an empty matching seat


@dataclass(frozen=True, slots=True)
class CardDef:
    """One printed card. Immutable and shared across cloned game states."""

    name: str
    kind: CardKind
    #: Estate restriction. ``None`` means "any estate" (the wildcard cards).
    estate: Estate | None = None
    #: For courtier cards: the epithet in the courtier table.
    courtier: str | None = None
    #: Events only: "minor" (target may save) or "major" (no save).
    tier: str | None = None
    #: Events only: which primitive above the card applies.
    effect: str | None = None
    #: Whether the target may attempt a d6 save.
    save: bool = False
    #: Strips/mutations: which attribute the card touches.
    attribute: str | None = None
    #: Mutations: the destination value, or ``None`` when the player chooses.
    value: str | None = None

    @property
    def is_courtier(self) -> bool:
        return self.kind is CardKind.COURTIER


def _courtier_cards() -> list[CardDef]:
    return [
        CardDef(c.name, CardKind.COURTIER, estate=c.estate, courtier=c.name)
        for c in COURTIERS
    ]


#: Each of the ten events does something the other nine do not. The minor five
#: allow the target a save; the major five do not, and no Defense covers any of
#: them.
EVENT_CARDS: tuple[CardDef, ...] = (
    # --- Minor: the target may attempt a d6 save ---------------------------
    #: Sent away from court, but not out of it.
    CardDef("Quarantine", CardKind.EVENT, tier="minor", effect=EFFECT_DEMOTE, save=True),
    #: Dead, though the epithet may return on somebody new.
    CardDef("Poisoning at the Feast", CardKind.EVENT, tier="minor", effect=EFFECT_REMOVE, save=True),
    #: Carried off down the trade road and back into the deck.
    CardDef("Caravan", CardKind.EVENT, tier="minor", effect=EFFECT_RECALL, save=True),
    #: Their patron's money is worthless; the protection lapses.
    CardDef("Debasement of the Coinage", CardKind.EVENT, tier="minor", effect=EFFECT_BREAK_DEFENSE, save=True),
    #: The sky goes dark and the omens with it: faith stripped to none.
    CardDef("Eclipse", CardKind.EVENT, tier="minor", effect=EFFECT_STRIP_FAITH, save=True),
    # --- Major: no save ----------------------------------------------------
    #: Starved out of the seat, and no bodyguard gets in.
    CardDef("Siege", CardKind.EVENT, tier="major", effect=EFFECT_DEMOTE_AND_BREAK),
    #: Out of the game entirely -- the one death nobody comes back from.
    CardDef("Plague", CardKind.EVENT, tier="major", effect=EFFECT_ERASE),
    #: A windfall: install them from the outer circle for free.
    CardDef("Treasure Fleet", CardKind.EVENT, tier="major", effect=EFFECT_INSTALL),
    #: The house cannot feed its own: family stripped to none.
    CardDef("Famine", CardKind.EVENT, tier="major", effect=EFFECT_STRIP_FAMILY),
    #: Ruined to the commons, and unseated if the seat no longer fits.
    CardDef("Meteor", CardKind.EVENT, tier="major", effect=EFFECT_RUIN),
)

PROMOTION_CARDS: tuple[CardDef, ...] = (
    CardDef("Promotion", CardKind.PROMOTION),
    CardDef("Battlefield Promotion", CardKind.PROMOTION, estate=Estate.MILITARY),
    CardDef("Consecration", CardKind.PROMOTION, estate=Estate.CHURCH),
    CardDef("Royal Charter", CardKind.PROMOTION, estate=Estate.MERCHANT),
    CardDef("Acclamation", CardKind.PROMOTION, estate=Estate.COMMONS),
)

DEMOTION_CARDS: tuple[CardDef, ...] = (
    CardDef("Demotion", CardKind.DEMOTION),
    CardDef("Heresy Accusation", CardKind.DEMOTION, estate=Estate.CHURCH),
    CardDef("Cashiering", CardKind.DEMOTION, estate=Estate.MILITARY),
    CardDef("Charter Revoked", CardKind.DEMOTION, estate=Estate.MERCHANT),
    CardDef("Ostracism", CardKind.DEMOTION, estate=Estate.COMMONS),
)

REMOVAL_CARDS: tuple[CardDef, ...] = (
    CardDef("Assassination", CardKind.REMOVAL),
    CardDef("Targeted Poisoning", CardKind.REMOVAL, save=True),
    CardDef("Martyrdom", CardKind.REMOVAL, estate=Estate.CHURCH),
    CardDef("Battlefield Betrayal", CardKind.REMOVAL, estate=Estate.MILITARY),
    CardDef("Bankruptcy", CardKind.REMOVAL, estate=Estate.MERCHANT),
    CardDef("Mob Violence", CardKind.REMOVAL, estate=Estate.COMMONS),
)

#: The estate on a defense card is the estate of the courtier it costs to play.
DEFENSE_CARDS: tuple[CardDef, ...] = (
    CardDef("Patron Protection", CardKind.DEFENSE),
    CardDef("Sanctuary", CardKind.DEFENSE, estate=Estate.CHURCH),
    CardDef("Bodyguard", CardKind.DEFENSE, estate=Estate.MILITARY),
    CardDef("Deep Pockets", CardKind.DEFENSE, estate=Estate.MERCHANT),
    CardDef("Popularity", CardKind.DEFENSE, estate=Estate.COMMONS),
)

STRIP_CARDS: tuple[CardDef, ...] = (
    CardDef("Castration", CardKind.STRIP, attribute="family", value=Family.NONE.value),
    CardDef("Excommunication", CardKind.STRIP, attribute="faith", value=Faith.NONE.value),
)

MUTATION_CARDS: tuple[CardDef, ...] = (
    CardDef("Take Up the Sword", CardKind.MUTATION, attribute="estate", value=Estate.MILITARY.value),
    CardDef("Take Vows", CardKind.MUTATION, attribute="estate", value=Estate.CHURCH.value),
    CardDef("Enter Trade", CardKind.MUTATION, attribute="estate", value=Estate.MERCHANT.value),
    CardDef("Lose Status", CardKind.MUTATION, attribute="estate", value=Estate.COMMONS.value),
    # Conversion flips the two faiths; on a godless or a stripped courtier
    # the player picks which faith they come to.
    CardDef("Conversion", CardKind.MUTATION, attribute="faith"),
    # Apostasy pushes a courtier out of faith altogether.
    CardDef("Apostasy", CardKind.MUTATION, attribute="faith", value=Faith.GODLESS.value),
    CardDef("Go Native", CardKind.MUTATION, attribute="origin", value=Origin.BARBARIAN.value),
    CardDef("Assimilate", CardKind.MUTATION, attribute="origin", value=Origin.IMPERIAL.value),
    # Adoption takes its value from the family courtier sacrificed from hand.
    CardDef("Adoption", CardKind.MUTATION, attribute="family"),
)

PIVOT_CARDS: tuple[CardDef, ...] = (
    CardDef("Schismatic Event", CardKind.PIVOT),
)

OUTMANEUVER_CARD = CardDef("Outmaneuver", CardKind.OUTMANEUVER)


def build_cards(outmaneuver_copies: int = 1) -> tuple[CardDef, ...]:
    """Return every card in the play deck, indexed by position (its uid)."""

    cards: list[CardDef] = []
    cards.extend(_courtier_cards())
    cards.extend(EVENT_CARDS)
    cards.extend(PROMOTION_CARDS)
    cards.extend(DEMOTION_CARDS)
    cards.extend(REMOVAL_CARDS)
    cards.extend(DEFENSE_CARDS)
    cards.extend(STRIP_CARDS)
    cards.extend(MUTATION_CARDS)
    cards.extend(PIVOT_CARDS)
    cards.extend(OUTMANEUVER_CARD for _ in range(outmaneuver_copies))
    return tuple(cards)
