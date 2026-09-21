"""What gets printed on each card, in the wording of docs/RULES.md.

`succession/cards.py` is the mechanical truth -- kinds, estates, effects. This
module is the *presentation* half: the type line under a card's name and the
rules paragraph in its text box. Keeping it out of the package means the
simulator stays stdlib-only and untouched by anything the printer wants.

`tests/test_card_text.py` asserts that every card `build_cards()` deals has an
entry here, so a new card in the deck fails the suite instead of printing blank.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from succession.cards import CardDef  # noqa: E402
from succession.enums import SEAT_ESTATE, CardKind, Estate, Seat  # noqa: E402

#: Shown under the name of every card that is not a courtier, in small caps.
ANY_ESTATE = "Any Estate"

#: The rules text printed in each action card's text box. Courtiers carry an
#: attribute block instead -- their epithet is the whole of their rules.
RULES: dict[str, str] = {
    # --- Events -------------------------------------------------------------
    # Every event hits the whole table, and no Defense covers one. A freeze
    # runs until just before the caster's next turn, so every other player
    # takes exactly one turn under it.
    "Quarantine": (
        "The seats are sealed until just before your next turn. No promotion, "
        "no demotion, no move into an empty seat, and no Defense attached. A "
        "seated courtier cannot be removed, stripped or mutated. The outer "
        "circle plays on."
    ),
    "Siege": (
        "The board is sealed until just before your next turn. Nothing enters "
        "it, leaves it or changes on it. Discarding, Outmaneuver, Schismatic "
        "Event and the non-purge events still work."
    ),
    "Poisoning at the Feast": (
        "Starting with you and going clockwise, every player names one "
        "courtier in play, and that courtier dies. Each names against the "
        "board as it then stands. A named courtier rolls a d6 and survives "
        "on an even."
    ),
    "Plague": (
        "Starting with you and going clockwise, every player names one "
        "courtier in play, and that courtier dies. Each names against the "
        "board as it then stands. Nobody is spared."
    ),
    "Caravan": (
        "Every player draws a card, starting with you and going clockwise. A "
        "hand already holding seven draws nothing."
    ),
    "Treasure Fleet": (
        "Every player draws two cards, starting with you and going clockwise. "
        "A hand already holding seven draws nothing."
    ),
    "Debasement of the Coinage": (
        "Every player discards a card, starting with you and going clockwise."
    ),
    "Famine": (
        "Every player discards two cards, starting with you and going "
        "clockwise."
    ),
    "Eclipse": (
        "Shuffle the discard pile back into the deck. This card resolves "
        "first and then goes to the new discard."
    ),
    "Meteor": (
        "Every hand is shuffled into the deck and dealt back out. Each player "
        "receives as many cards as they were holding."
    ),
    # --- Promotions ---------------------------------------------------------
    "Promotion": (
        "Move an outer-circle courtier into an occupied seat of their estate. "
        "The sitting courtier is bumped to the outer circle."
    ),
    "Battlefield Promotion": (
        "Move an outer-circle Military courtier into an occupied Military "
        "seat. The sitting courtier is bumped to the outer circle."
    ),
    "Consecration": (
        "Move an outer-circle Church courtier into an occupied Church seat. "
        "The sitting courtier is bumped to the outer circle."
    ),
    "Royal Charter": (
        "Move an outer-circle Merchant courtier into an occupied Merchant "
        "seat. The sitting courtier is bumped to the outer circle."
    ),
    "Acclamation": (
        "Move an outer-circle Commons courtier into the Voice of the People's seat. "
        "The sitting courtier is bumped to the outer circle."
    ),
    # --- Demotions ----------------------------------------------------------
    "Demotion": (
        "Send an inner-circle courtier to the outer circle. Their seat is "
        "left empty."
    ),
    "Heresy Accusation": (
        "Send an inner-circle Church courtier to the outer circle. Their seat "
        "is left empty."
    ),
    "Cashiering": (
        "Send an inner-circle Military courtier to the outer circle. Their "
        "seat is left empty."
    ),
    "Charter Revoked": (
        "Send an inner-circle Merchant courtier to the outer circle. Their "
        "seat is left empty."
    ),
    "Ostracism": (
        "Send the Voice of the People to the outer circle. The seat is left empty."
    ),
    # --- Removals -----------------------------------------------------------
    # A killed courtier goes to the discard and may be shuffled back in as a
    # new person carrying the printed attributes, never the accumulated ones.
    "Assassination": (
        "A courtier anywhere in play leaves play. They go to the discard and "
        "may return later as a new person with their printed attributes."
    ),
    "Targeted Poisoning": (
        "A courtier anywhere in play leaves play, unless they roll a d6 and "
        "survive on an even. A Defense is spent before the roll is made."
    ),
    "Martyrdom": (
        "A Church courtier leaves play. They go to the discard and may return "
        "later as a new person with their printed attributes."
    ),
    "Battlefield Betrayal": (
        "A Military courtier leaves play. They go to the discard and may "
        "return later as a new person with their printed attributes."
    ),
    "Bankruptcy": (
        "A Merchant courtier leaves play. They go to the discard and may "
        "return later as a new person with their printed attributes."
    ),
    "Mob Violence": (
        "A Commons courtier leaves play. They go to the discard and may "
        "return later as a new person with their printed attributes."
    ),
    # --- Defenses -----------------------------------------------------------
    # The estate on a defense is the estate of the courtier it costs, not of
    # the courtier it guards: any inner-circle courtier may be shielded.
    "Patron Protection": (
        "Sacrifice a courtier of any estate from your hand and attach this to "
        "any inner-circle courtier. It negates the first Removal, Demotion, "
        "Strip or Mutation aimed at them, then is discarded. It does not stop "
        "an Event."
    ),
    "Sanctuary": (
        "Sacrifice a Church courtier from your hand and attach this to any "
        "inner-circle courtier. It negates the first Removal, Demotion, Strip "
        "or Mutation aimed at them, then is discarded. It does not stop an "
        "Event."
    ),
    "Bodyguard": (
        "Sacrifice a Military courtier from your hand and attach this to any "
        "inner-circle courtier. It negates the first Removal, Demotion, Strip "
        "or Mutation aimed at them, then is discarded. It does not stop an "
        "Event."
    ),
    "Deep Pockets": (
        "Sacrifice a Merchant courtier from your hand and attach this to any "
        "inner-circle courtier. It negates the first Removal, Demotion, Strip "
        "or Mutation aimed at them, then is discarded. It does not stop an "
        "Event."
    ),
    "Popularity": (
        "Sacrifice a Commons courtier from your hand and attach this to any "
        "inner-circle courtier. It negates the first Removal, Demotion, Strip "
        "or Mutation aimed at them, then is discarded. It does not stop an "
        "Event."
    ),
    # --- Strips -------------------------------------------------------------
    # A strip empties the slot without spending the courtier's one mutation,
    # so the attribute can be filled again later.
    "Castration": (
        "A courtier's Family becomes None. They keep their seat. A strip does "
        "not spend a mutation, so Adoption can give them a family again."
    ),
    "Excommunication": (
        "A courtier's Faith becomes None. They keep their seat. A strip does "
        "not spend a mutation, so Conversion can bring them to a faith again."
    ),
    # --- Mutations ----------------------------------------------------------
    # Each attribute may be mutated at most once per courtier.
    "Take Up the Sword": (
        "A courtier's Estate becomes Military. If that un-matches the seat "
        "they hold, they are demoted to the outer circle at once."
    ),
    "Take Vows": (
        "A courtier's Estate becomes Church. If that un-matches the seat they "
        "hold, they are demoted to the outer circle at once."
    ),
    "Enter Trade": (
        "A courtier's Estate becomes Merchant. If that un-matches the seat "
        "they hold, they are demoted to the outer circle at once."
    ),
    "Lose Status": (
        "A courtier's Estate becomes Commons. If that un-matches the seat "
        "they hold, they are demoted to the outer circle at once."
    ),
    "Conversion": (
        "A courtier's Faith becomes any faith but their own; you choose it. A "
        "godless or excommunicated courtier may be brought to any of the "
        "three."
    ),
    "Apostasy": (
        "A courtier's Faith becomes Godless. Godlessness has no agenda, so "
        "their seat is one no faith can count."
    ),
    "Go Native": "A courtier's Origin becomes Barbarian.",
    "Assimilate": "A courtier's Origin becomes Imperial.",
    "Adoption": (
        "Sacrifice a courtier of a family from your hand. The target takes "
        "that family as their own."
    ),
    # --- Pivot and Outmaneuver ----------------------------------------------
    "Schismatic Event": (
        "Discard your agenda and draw a new one from the pool of agendas "
        "nobody was dealt. The act is public; both agendas stay private."
    ),
    "Outmaneuver": (
        "The targeted player skips their next turn entirely, draw included."
    ),
}

#: A one-line reminder printed under the rules text, per kind.
REMINDERS: dict[CardKind, str] = {
    CardKind.EVENT: "Hits every player. No Defense stops an Event.",
    CardKind.MUTATION: "Each attribute may be mutated once per courtier.",
    CardKind.STRIP: "A strip does not spend a mutation.",
    CardKind.DEFENSE: "Attaches to an inner-circle courtier only.",
}

#: The eight agendas, for the optional text-only agenda cards. The numbers are
#: the defaults in `succession/agendas.py`; a table running a variant should
#: regenerate with the matching flags rather than trust the print.
AGENDA_TEXT: tuple[tuple[str, str, str], ...] = (
    (
        "House Rising: Amonides",
        "House Amonides",
        "Three or more of the seven inner seats are held by courtiers of "
        "House Amonides, at least one of them a Church seat -- the house's "
        "own estate.",
    ),
    (
        "House Rising: Mitreas",
        "House Mitreas",
        "Three or more of the seven inner seats are held by courtiers of "
        "House Mitreas, at least one of them a Merchant seat -- the house's "
        "own estate.",
    ),
    (
        "House Rising: Argaian",
        "House Argaian",
        "Three or more of the seven inner seats are held by courtiers of "
        "House Argaian, at least one of them a Military seat -- the house's "
        "own estate.",
    ),
    (
        "Faith Ascendant: Old Gods",
        "The Old Gods",
        "Four or more of the seven inner seats are held by courtiers of the "
        "Old Gods.",
    ),
    (
        "Faith Ascendant: Mystery Cults",
        "The Mystery Cults",
        "Four or more of the seven inner seats are held by courtiers of the "
        "Mystery Cults.",
    ),
    (
        "Faith Ascendant: The One God",
        "The One God",
        "Four or more of the seven inner seats are held by courtiers of The "
        "One God.",
    ),
    (
        "Barbarian Conquest",
        "The Frontier",
        "Three courtiers of Barbarian origin hold inner seats, in any estates.",
    ),
    (
        "Balance",
        "The Settlement",
        "Six of the seven seats are filled, and the inner circle shows all "
        "three families, all three faiths, and two barbarians at once.",
    ),
)


#: Separates the kind from its qualifier on a printed type line.
SEP = " \u00b7 "


#: The line on a seat card, under the name. Paired seats say so, because the
#: engine treats the two members of a pair as interchangeable and a table
#: should not waste time deciding which Church chair somebody is sitting in.
SEAT_TEXT: dict[Seat, str] = {
    Seat.ARCHPRIEST: (
        "One of the two Church seats, which are interchangeable. Only a "
        "courtier whose current estate is Church may sit here."
    ),
    Seat.ORACLE: (
        "One of the two Church seats, which are interchangeable. Only a "
        "courtier whose current estate is Church may sit here."
    ),
    Seat.LORD_GENERAL: (
        "One of the two Military seats, which are interchangeable. Only a "
        "courtier whose current estate is Military may sit here."
    ),
    Seat.CAPTAIN_OF_THE_GUARD: (
        "One of the two Military seats, which are interchangeable. Only a "
        "courtier whose current estate is Military may sit here."
    ),
    Seat.KEEPER_OF_THE_TREASURY: (
        "One of the two Merchant seats, which are interchangeable. Only a "
        "courtier whose current estate is Merchant may sit here."
    ),
    Seat.MASTER_OF_THE_MARKET: (
        "One of the two Merchant seats, which are interchangeable. Only a "
        "courtier whose current estate is Merchant may sit here."
    ),
    Seat.VOICE_OF_THE_PEOPLE: (
        "The court's only Commons seat. A house reaches it solely through its "
        "charioteer, the one commoner it fields."
    ),
}

#: Printed on every seat card, under a rule. The rules that govern a chair
#: rather than the person in it.
SEAT_REMINDER = (
    "Move a matching outer courtier into this seat for free when it is empty. "
    "A Promotion takes it while filled, bumping the sitter out. A Demotion "
    "empties it. A courtier mutated out of this estate is demoted at once."
)


def seat_type_line(seat: Seat) -> str:
    """e.g. "Seat . Church"."""

    return f"Seat{SEP}{SEAT_ESTATE[seat].value}"


def seats_by_estate() -> list[tuple[Estate, list[Seat]]]:
    """The seven seats grouped by estate, in board order."""

    grouped: list[tuple[Estate, list[Seat]]] = []
    for seat, estate in SEAT_ESTATE.items():
        if grouped and grouped[-1][0] is estate:
            grouped[-1][1].append(seat)
        else:
            grouped.append((estate, [seat]))
    return grouped


def type_line(card: CardDef) -> str:
    """The small-caps line under a card's name, e.g. "Removal . Church"."""

    kind = card.kind.value
    if card.kind is CardKind.COURTIER:
        return f"Courtier{SEP}{card.estate.value}" if card.estate else "Courtier"
    if card.kind is CardKind.EVENT:
        return f"Event{SEP}{card.tier.capitalize()}" if card.tier else "Event"
    if card.kind in (CardKind.STRIP, CardKind.MUTATION):
        return f"{kind}{SEP}{card.attribute.capitalize()}" if card.attribute else kind
    if card.kind in (CardKind.PIVOT, CardKind.OUTMANEUVER):
        return kind
    return f"{kind}{SEP}{card.estate.value if card.estate else ANY_ESTATE}"


def rules_for(card: CardDef) -> str:
    """The card's rules paragraph. Raises on a card nobody has written text for."""

    try:
        return RULES[card.name]
    except KeyError:  # pragma: no cover - guarded by tests/test_card_text.py
        raise KeyError(
            f"No printed rules text for {card.name!r}. Add it to RULES in "
            f"tools/card_text.py."
        ) from None
