"""A stacked deal: a game set up the way it is needed, not the way a seed falls.

A deal names what matters and leaves the rest to the shuffle:

    {
        "first": 0,                                   # who moves first
        "agendas": {"0": "house_mitreas"},     # seat -> agenda key
        "hands": {"0": ["Golden Thumb", "Promotion"]},  # seat -> whole starting hand
        "deck": ["Debasement of the Coinage"],        # the next draws, in order
        "seats": {"Oracle": "Hand of the Oracle"},    # inner seats already held
        "outer": ["Silver Tongue"],                   # the outer circle
    }

Every key is optional. Seats are indices into `Config.players`, which a deal
never shuffles. A seat without a hand is dealt `starting_hand` cards as usual,
agendas not named are drawn at random from the rest of the pool, and `first`
defaults to seat 0. Cards are named as printed; a card named twice takes a
second copy, if the deck has one.

Tests use deals so that changing the deck or the rules cannot quietly move
the situation they are about, as it moves every seed; the first game a new
player sees is a deal too. A game record carries its deal, so it replays.
"""

from __future__ import annotations

import random
from typing import Optional

from .agendas import AGENDAS
from .engine import draw
from .enums import Seat
from .state import Config, GameState

#: The first game a new player is dealt: they move first, with House Rising:
#: Mitreas and two Mitreas courtiers in hand, one of them for the Merchant
#: seat House Rising wants.
FIRST_GAME: dict = {
    "first": 0,
    "agendas": {"0": "house_mitreas"},
    "hands": {"0": ["Golden Thumb", "Rider of the Long Road", "Promotion", "Battlefield Promotion", "Bodyguard"]},
}

NAMED: dict[str, dict] = {"first_game": FIRST_GAME}


def resolve(deal) -> Optional[dict]:
    """A deal given by name ("first_game") or in full; None for none."""

    if deal is None or isinstance(deal, dict):
        return deal
    try:
        return NAMED[deal]
    except KeyError:
        raise ValueError(f"unknown deal {deal!r} (have: {', '.join(NAMED)})") from None


def setup(config: Config, rng: random.Random, deal: dict, *, trace: bool = False) -> GameState:
    state = GameState.new(config)
    state.trace = trace
    n = config.num_players

    left: dict[str, list[int]] = {}
    for uid, card in enumerate(state.cards):
        left.setdefault(card.name, []).append(uid)

    def take(name: str) -> int:
        copies = left.get(name)
        if not copies:
            raise ValueError(f"the deal asks for {name!r}, and no copy of it is left in the deck")
        return copies.pop(0)

    def seat_index(key) -> int:
        seat = int(key)
        if not 0 <= seat < n:
            raise ValueError(f"the deal names seat {seat}, and there are {n} players")
        return seat

    # Agendas: the named ones, then the rest of the pool at random.
    fixed = {seat_index(k): v for k, v in deal.get("agendas", {}).items()}
    pool = [a.key for a in AGENDAS if a.key not in config.excluded_agendas and a.key not in fixed.values()]
    unknown = set(fixed.values()) - {a.key for a in AGENDAS}
    if unknown:
        raise ValueError(f"unknown agenda(s) in the deal: {', '.join(sorted(unknown))}")
    rng.shuffle(pool)
    state.agendas = [fixed[p] if p in fixed else pool.pop() for p in range(n)]
    state.unused_agendas = pool

    for seat, name in deal.get("seats", {}).items():
        state.seats[Seat(seat)] = take(name)
    state.outer = [take(name) for name in deal.get("outer", [])]
    hands = {seat_index(k): [take(name) for name in names] for k, names in deal.get("hands", {}).items()}
    top = [take(name) for name in deal.get("deck", [])]

    # Everything not named is shuffled into the deck, and the other hands are
    # dealt from it as usual (an event dealt goes back in).
    state.deck = sorted(uid for copies in left.values() for uid in copies)
    rng.shuffle(state.deck)
    for p, hand in hands.items():
        state.hands[p] = hand
    for _ in range(config.starting_hand):
        for p in range(n):
            if p not in hands:
                draw(state, p, rng, dealing=True)
    # The deck is drawn from its end: the named top goes on last.
    state.deck.extend(reversed(top))
    state.current = seat_index(deal.get("first", 0))
    return state
