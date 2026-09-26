"""The tutorial: a short, set game that teaches the rules by playing them.

You hold House Rising: Mitreas against one rival, who holds Faith Ascendant:
Old Gods. The board is set so the lesson happens in three of your turns:

1. Your first draw is a Caravan -- an event, played the moment it is drawn.
   Then the rival is one move from winning (three Old Gods seated, a fourth
   waiting for the empty Captain's chair), and you stop them: Apostasy turns
   one of their seated courtiers godless.
2. The Caravan brought you Buyer of Cities. You play him to the outer circle.
3. You move him into the empty Master of the Market -- three Mitreas seats, one
   of them a Merchant seat -- and win.

Each of your turns offers only the move the lesson is about (falling back to
every legal move should the board ever not allow it), and the rival is
scripted, so the game goes the same way every time. `coach()` is what the page
says at each step.
"""

from __future__ import annotations

import random
from typing import Optional, Sequence

from .actions import DISCARD, MOVE, PASS, PLAY, Action
from .bots import Bot
from .enums import SEATS, CardKind, Faith, Seat
from .state import Config, GameState

NAME = "tutorial"
#: The rival's seat type; the page names it "Rival".
TUTOR = "tutor"

AGENDAS = ["house_mitreas", "faith_old_gods"]

SEATED = {
    Seat.ARCHPRIEST: "Beloved of the Gods",  # Old Gods
    Seat.ORACLE: "Hand of the Oracle",  # Old Gods
    Seat.LORD_GENERAL: "Keeper of the Long Peace",  # Old Gods
    Seat.KEEPER_OF_THE_TREASURY: "Golden Thumb",  # Mitreas, in a Merchant seat
    Seat.VOICE_OF_THE_PEOPLE: "Charioteer of the Seven Turns",  # Mitreas
}
#: The rival's fourth Old Gods courtier, waiting for the Captain's chair.
THREAT = "Speaker of the Old Words"
#: Your third Mitreas courtier, who arrives with the Caravan.
ALLY = "Buyer of Cities"
THWART = "Apostasy"
EVENT = "Caravan"

YOUR_HAND = [THWART, "Deep Pockets", "Mender of Bones", "Silver Tongue", "Demotion"]
RIVAL_HAND = ["Reader of Omens", "Founder of Markets", "Consecration", "Popularity", "Taker of the Citadel"]


def config() -> Config:
    return Config(players=("human", TUTOR), shuffle_seats=False)


def setup(config: Config, rng: random.Random, *, trace: bool = True) -> GameState:
    """The board as the lesson opens, and the deck stacked for it."""

    state = GameState.new(config)
    state.trace = trace
    uid = {card.name: i for i, card in enumerate(state.cards)}

    state.agendas = list(AGENDAS)
    state.unused_agendas = [key for key in _agenda_keys() if key not in AGENDAS]
    for seat, name in SEATED.items():
        state.seats[seat] = uid[name]
    state.outer = [uid[THREAT]]
    state.hands = [[uid[n] for n in YOUR_HAND], [uid[n] for n in RIVAL_HAND]]

    # Everything else is the deck, with no other event in it: the lesson has
    # one. The top is dealt in this order -- your draw (the Caravan), the
    # Caravan's cards for you and the rival, then your own draw again.
    used = set(uid[n] for n in (*SEATED.values(), THREAT, *YOUR_HAND, *RIVAL_HAND, ALLY, EVENT))
    rest = [
        i
        for i, card in enumerate(state.cards)
        if i not in used and card.kind is not CardKind.EVENT
    ]
    rng.shuffle(rest)
    top = [uid[EVENT], uid[ALLY], rest.pop(), rest.pop()]  # popped from the end
    state.deck = rest + list(reversed(top))
    state.current = 0
    return state


def _agenda_keys() -> list[str]:
    from .agendas import AGENDA_KEYS

    return list(AGENDA_KEYS)


class Tutor(Bot):
    """The rival: seats their fourth Old Gods courtier if they can, else waits."""

    tier = TUTOR

    def choose(self, state: GameState, player: int, actions: Sequence[Action]) -> Action:
        threat = next((a for a in actions if a.kind == MOVE and state.name(a.courtier) == THREAT), None)
        if threat is not None:
            return threat
        return next((a for a in actions if a.kind == PASS), None) or next(
            a for a in actions if a.kind == DISCARD
        )

    def pick_courtier(self, state, player, candidates):
        return candidates[0]

    def pick_discard(self, state, player, hand):
        return hand[0]


def make_seat(tier: str, seat: int, rng: random.Random) -> Bot:
    return Tutor(seat, rng)


# -- your turns ---------------------------------------------------------------
def _lesson(state: GameState, action: Action, turn: int) -> bool:
    name = state.name
    if turn == 1:
        return (
            action.kind == PLAY
            and name(action.card) == THWART
            and state.seat_of(action.courtier) is not None
            and state.cstate[action.courtier].faith is Faith.OLD_GODS
        )
    if turn == 2:
        return action.kind == PLAY and name(action.card) == ALLY
    if turn == 3:
        return action.kind == MOVE and name(action.courtier) == ALLY
    return True


def allowed(state: GameState, turn: int, actions: list[Action]) -> list[Action]:
    """Your moves on your `turn`th turn: the lesson's, or all if it cannot be played."""

    lesson = [a for a in actions if _lesson(state, a, turn)]
    return lesson or actions


# -- what the page says -------------------------------------------------------
STEPS = 4


def coach(state: GameState, turn: int, over: bool, you_won: bool) -> Optional[dict]:
    """The coach's note for the moment: `turn` is how many of your turns have begun."""

    if over:
        if you_won:
            return {
                "step": STEPS,
                "title": "The court is yours",
                "text": (
                    "Three Mitreas courtiers hold inner seats, one of them a Merchant seat: House Rising: Mitreas "
                    "is complete, and the moment the board showed it, you won. In a real game every agenda is "
                    "secret, the rivals are cleverer, and there are more of them. Deal a game when you're ready."
                ),
            }
        return {
            "step": STEPS,
            "title": "The game is over",
            "text": "The tutorial went its own way this time. Deal a real game whenever you're ready.",
        }
    if turn == 0:
        return {
            "step": 0,
            "title": "Welcome to the court",
            "text": (
                "The seven chairs at the top are the inner circle. Your secret agenda, House Rising: Mitreas, wins "
                "the moment House Mitreas holds three of them, one a Merchant seat. You already hold two: Golden "
                "Thumb and the Charioteer of the Seven Turns."
            ),
        }
    if turn == 1:
        threat = state.name(state.outer[0]) if state.outer else THREAT
        return {
            "step": 1,
            "title": "An event, and a threat",
            "text": (
                "Your first draw was a Caravan: events play the moment they are drawn, for the whole table, and "
                "then you draw again. It brought you Buyer of Cities. Now look at your rival: three Old Gods "
                f"courtiers hold seats, and {threat} waits in the outer circle for the empty Captain of the Guard. "
                "Four Old Gods seats is Faith Ascendant -- they win next turn. Play Apostasy on one of their seated "
                "Old Gods: a godless courtier counts for no faith."
            ),
        }
    if turn == 2:
        return {
            "step": 2,
            "title": "Thwarted",
            "text": (
                "Your rival took the Captain's chair anyway, but three Old Gods seats is not four. Now build your "
                "own: play Buyer of Cities from your hand. A courtier you play goes to the outer circle, never "
                "straight into a seat."
            ),
        }
    return {
        "step": 3,
        "title": "Take the seat",
        "text": (
            "Moving a courtier from the outer circle into an empty seat of their estate costs no card. Buyer of "
            "Cities is a Merchant, and the Master of the Market's chair is empty. Move him there."
        ),
    }
