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

# --- Event effects ----------------------------------------------------------
# Events are not aimed at a courtier: each one hits the whole table. They come
# in five minor/major pairs, the major being the harsher version of the minor.
EFFECT_FREEZE_INNER = "freeze_inner"   # the inner circle cannot change for a round
EFFECT_FREEZE_BOARD = "freeze_board"   # nothing on the board can change for a round
EFFECT_PURGE = "purge"                 # every player names a courtier to kill
EFFECT_DRAW_ALL = "draw_all"           # every player draws
EFFECT_DISCARD_ALL = "discard_all"     # every player discards
EFFECT_RESHUFFLE = "reshuffle"         # the discard pile is shuffled back into the deck
EFFECT_REDEAL = "redeal"               # every hand is shuffled in and dealt back out


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
    #: Events only: how many cards the effect moves, or how many rounds it lasts.
    amount: int = 1
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


#: Ten events in five pairs: a minor version and a harsher major one. Only the
#: purge pair has anything to save against, and only its minor half allows it.
EVENT_CARDS: tuple[CardDef, ...] = (
    #: The court is sealed: no seat changes hands for a round.
    CardDef("Quarantine", CardKind.EVENT, tier="minor", effect=EFFECT_FREEZE_INNER),
    #: The whole city is shut in: nothing on the board moves for a round.
    CardDef("Siege", CardKind.EVENT, tier="major", effect=EFFECT_FREEZE_BOARD),
    #: Every player names a courtier to die; each may roll to survive.
    CardDef("Poisoning at the Feast", CardKind.EVENT, tier="minor", effect=EFFECT_PURGE, save=True),
    #: The same, and nobody is spared.
    CardDef("Plague", CardKind.EVENT, tier="major", effect=EFFECT_PURGE),
    #: Trade arrives: a card for every player.
    CardDef("Caravan", CardKind.EVENT, tier="minor", effect=EFFECT_DRAW_ALL, amount=1),
    #: A fleet arrives: two cards for every player.
    CardDef("Treasure Fleet", CardKind.EVENT, tier="major", effect=EFFECT_DRAW_ALL, amount=2),
    #: The coin is worthless: every player discards a card.
    CardDef("Debasement of the Coinage", CardKind.EVENT, tier="minor", effect=EFFECT_DISCARD_ALL, amount=1),
    #: The granaries are empty: every player discards two.
    CardDef("Famine", CardKind.EVENT, tier="major", effect=EFFECT_DISCARD_ALL, amount=2),
    #: The sky turns over: the discard pile is shuffled back into the deck.
    CardDef("Eclipse", CardKind.EVENT, tier="minor", effect=EFFECT_RESHUFFLE),
    #: Everything turns over: every hand is shuffled in and dealt back out.
    CardDef("Meteor", CardKind.EVENT, tier="major", effect=EFFECT_REDEAL),
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
