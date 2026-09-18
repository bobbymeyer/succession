"""The rules engine: action resolution, the turn loop, and win checking."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Optional

from .actions import DISCARD, MOVE, PASS, Action, install_seat_for, legal_actions
from .agendas import (
    AGENDAS,
    AGENDAS_BY_KEY,
    BoardCounts,
    count_board,
    progress_vector,
    rules_for,
    satisfied_counts,
)
from .cards import (
    EFFECT_BREAK_DEFENSE,
    EFFECT_DEMOTE,
    EFFECT_DEMOTE_AND_BREAK,
    EFFECT_INSTALL,
    EFFECT_RECALL,
    EFFECT_REMOVE,
    EFFECT_STRIP_FAITH,
)
from .courtiers import COURTIERS_BY_NAME
from .enums import DEFENDABLE, SEAT_ESTATE, CardKind, Estate, Faith, Family, Origin, Seat
from .state import Config, CourtierState, GameState


class EvalRng:
    """A deterministic stand-in for `random.Random` used in bot lookahead.

    Saves always fail (the attacker's optimistic view) and shuffles are no-ops,
    so evaluating the same action twice always gives the same board.
    """

    def randint(self, a: int, b: int) -> int:
        return a if a % 2 else a + 1  # an odd result: the save fails

    def randrange(self, n: int) -> int:
        return 0

    def shuffle(self, seq) -> None:
        return None

    def choice(self, seq):
        return seq[0]


_EVAL_RNG = EvalRng()


# --- zone plumbing ----------------------------------------------------------
def _detach_defense(state: GameState, uid: int) -> None:
    card = state.defenses.pop(uid, None)
    if card is not None:
        state.discard.append(card)


def _reset(state: GameState, uid: int) -> None:
    """Back to printed attributes: whoever returns bearing this epithet is new."""

    state.cstate[uid] = CourtierState.from_def(COURTIERS_BY_NAME[state.card(uid).courtier])


def _pull_from_play(state: GameState, uid: int) -> None:
    seat = state.seat_of(uid)
    if seat is not None:
        state.seats[seat] = None
    elif uid in state.outer:
        state.outer.remove(uid)
    _detach_defense(state, uid)


def demote(state: GameState, uid: int) -> bool:
    """Inner -> outer, leaving the seat empty. False if they were not seated."""

    seat = state.seat_of(uid)
    if seat is None:
        return False
    state.seats[seat] = None
    state.outer.append(uid)
    state.note(f"{state.name(uid)} demoted from {seat.value}")
    return True


def kill(state: GameState, uid: int) -> None:
    """Remove a courtier from the game.

    With `removed_courtiers_return_to_deck` the card goes to the discard, so a
    later reshuffle can bring the epithet back as a new person with printed
    attributes. Otherwise the card is out of the game for good.
    """

    _pull_from_play(state, uid)
    _reset(state, uid)
    if state.config.removed_courtiers_return_to_deck:
        state.discard.append(uid)
    else:
        state.removed.append(uid)
    state.bump("courtiers_killed")
    state.note(f"{state.name(uid)} removed from play")


def recall(state: GameState, uid: int, rng) -> None:
    """Courtier leaves the court and is shuffled back into the draw deck."""

    _pull_from_play(state, uid)
    _reset(state, uid)
    if state.deck:
        state.deck.insert(rng.randrange(len(state.deck) + 1), uid)
    else:
        state.deck.append(uid)
    state.bump("courtiers_recalled")
    state.note(f"{state.name(uid)} recalled into the deck")


def install(state: GameState, uid: int, seat: Seat) -> None:
    if uid in state.outer:
        state.outer.remove(uid)
    state.seats[seat] = uid


def _enforce_seat_estate(state: GameState, uid: int) -> None:
    """An estate mutation that un-matches a seat demotes its holder at once."""

    seat = state.seat_of(uid)
    if seat is not None and state.cstate[uid].estate is not SEAT_ESTATE[seat]:
        demote(state, uid)


def defense_absorbs(state: GameState, uid: int, kind: CardKind) -> bool:
    """Consume an attached defense if it covers this kind of attack."""

    if kind not in DEFENDABLE:
        return False
    card = state.defenses.get(uid)
    if card is None:
        return False
    del state.defenses[uid]
    state.discard.append(card)
    state.bump("defenses_triggered")
    state.note(f"{state.name(card)} protects {state.name(uid)}")
    return True


def save_roll(state: GameState, rng) -> bool:
    """A d6 save: successful on an even roll."""

    roll = rng.randint(1, 6)
    return (roll % 2 == 0) if state.config.save_on_even else (roll % 2 == 1)


# --- drawing ----------------------------------------------------------------
def draw(state: GameState, player: int, rng, count: int = 1) -> None:
    for _ in range(count):
        if len(state.hands[player]) >= state.config.hand_limit:
            return
        if not state.deck:
            if not state.discard:
                return
            state.deck = state.discard
            state.discard = []
            rng.shuffle(state.deck)
            state.reshuffles += 1
            state.bump("reshuffles")
        state.hands[player].append(state.deck.pop())


# --- resolution -------------------------------------------------------------
def apply_action(state: GameState, player: int, action: Action, rng) -> None:
    """Resolve one action. The board is fully updated when this returns."""

    state.bump(f"action_{action.kind}")

    if action.kind == PASS:
        return

    if action.kind == MOVE:
        install(state, action.courtier, action.seat)
        state.bump("moves")
        state.note(f"P{player} moves {state.name(action.courtier)} into {action.seat.value}")
        return

    hand = state.hands[player]
    hand.remove(action.card)

    if action.kind == DISCARD:
        state.discard.append(action.card)
        state.note(f"P{player} discards {state.name(action.card)}")
        return

    card = state.card(action.card)
    state.bump(f"played_{card.kind.value.lower()}")
    state.note(f"P{player} {action.describe(state)}")

    if card.is_courtier:
        # The one place a card from hand lands: the outer circle.
        state.outer.append(action.card)
        return

    if action.sacrifice >= 0:
        hand.remove(action.sacrifice)
        state.discard.append(action.sacrifice)
        state.bump("courtiers_sacrificed")

    if _resolve(state, player, action, card, rng):
        state.discard.append(action.card)


def _resolve(state: GameState, player: int, action: Action, card, rng) -> bool:
    """Resolve a non-courtier card. Returns False if it stays on the table."""

    kind = card.kind
    target = action.courtier

    if kind is CardKind.PROMOTION:
        bumped = state.seats[action.seat]
        if bumped is not None:
            state.seats[action.seat] = None
            state.outer.append(bumped)
        install(state, target, action.seat)
        return True

    if kind is CardKind.DEMOTION:
        if not defense_absorbs(state, target, kind):
            demote(state, target)
        return True

    if kind is CardKind.REMOVAL:
        if defense_absorbs(state, target, kind):
            return True
        if card.save and save_roll(state, rng):
            state.bump("saves_made")
            state.note(f"{state.name(target)} saves against {card.name}")
            return True
        kill(state, target)
        return True

    if kind is CardKind.DEFENSE:
        # The defense stays attached face-up; it is discarded when it triggers.
        state.defenses[target] = action.card
        state.note(f"{card.name} attached to {state.name(target)}")
        return False

    if kind is CardKind.STRIP:
        if not defense_absorbs(state, target, kind):
            value = Family.NONE if card.attribute == "family" else Faith.NONE
            # A strip does not consume the once-per-courtier mutation allowance.
            state.cstate[target] = state.cstate[target].with_attribute(
                card.attribute, value, is_mutation=False
            )
        return True

    if kind is CardKind.MUTATION:
        if not defense_absorbs(state, target, kind):
            value = _mutation_value(card.attribute, action.value)
            state.cstate[target] = state.cstate[target].with_attribute(
                card.attribute, value, is_mutation=True
            )
            if card.attribute == "estate":
                _enforce_seat_estate(state, target)
        return True

    if kind is CardKind.EVENT:
        # Defenses explicitly do not cover events.
        if card.save and save_roll(state, rng):
            state.bump("saves_made")
            state.note(f"{state.name(target)} saves against {card.name}")
            return True
        _resolve_event(state, card.effect, target, rng)
        return True

    if kind is CardKind.OUTMANEUVER:
        state.skip_next[action.player] = True
        state.note(f"P{action.player} will skip their next turn")
        return True

    if kind is CardKind.PIVOT:
        old = state.agendas[player]
        pick = rng.randrange(len(state.unused_agendas))
        state.agendas[player] = state.unused_agendas.pop(pick)
        state.unused_agendas.append(old)
        state.revealed[player] = False
        state.bump("pivots")
        return True

    raise ValueError(f"unresolvable card kind: {kind}")  # pragma: no cover


def _mutation_value(attribute: str, raw: str):
    if attribute == "estate":
        return Estate(raw)
    if attribute == "faith":
        return Faith(raw)
    if attribute == "family":
        return Family(raw)
    return Origin(raw)


def _resolve_event(state: GameState, effect: str, target: int, rng) -> None:
    if effect == EFFECT_DEMOTE:
        demote(state, target)
    elif effect == EFFECT_REMOVE:
        kill(state, target)
    elif effect == EFFECT_RECALL:
        recall(state, target, rng)
    elif effect == EFFECT_STRIP_FAITH:
        state.cstate[target] = state.cstate[target].with_attribute(
            "faith", Faith.NONE, is_mutation=False
        )
    elif effect == EFFECT_BREAK_DEFENSE:
        if target in state.defenses:
            _detach_defense(state, target)
        else:
            demote(state, target)
    elif effect == EFFECT_DEMOTE_AND_BREAK:
        _detach_defense(state, target)
        demote(state, target)
    elif effect == EFFECT_INSTALL:
        seat = install_seat_for(state, target)
        if seat is not None:
            install(state, target, seat)
    else:  # pragma: no cover
        raise ValueError(f"unknown event effect: {effect}")


def simulate(state: GameState, player: int, action: Action) -> GameState:
    """Apply `action` to a copy of `state` -- the bots' one-ply lookahead."""

    nxt = state.clone()
    apply_action(nxt, player, action, _EVAL_RNG)
    return nxt


# --- win checking -----------------------------------------------------------
def check_winners(state: GameState) -> list[int]:
    """Players whose agenda the board satisfies right now (ties: everyone wins)."""

    counts = count_board(state)
    rules = rules_for(state)
    return [
        p
        for p in range(state.config.num_players)
        if satisfied_counts(counts, AGENDAS_BY_KEY[state.agendas[p]], rules)
    ]


# --- the game ---------------------------------------------------------------
@dataclass
class GameResult:
    game_id: int
    seed: int
    turns: int
    rounds: int
    timeout: bool
    winners: list[int]
    tiers: list[str]
    agendas: list[str]
    board: dict[str, str]
    counts: "BoardCounts"
    stats: dict[str, int]
    reshuffles: int
    final_state: Optional[GameState] = None

    @property
    def winning_agendas(self) -> list[str]:
        return [self.agendas[p] for p in self.winners]

    @property
    def winning_tiers(self) -> list[str]:
        return [self.tiers[p] for p in self.winners]


def setup_game(config: Config, rng: random.Random, *, trace: bool = False) -> GameState:
    state = GameState.new(config)
    state.trace = trace

    keys = [a.key for a in AGENDAS]
    rng.shuffle(keys)
    state.agendas = keys[: config.num_players]
    state.unused_agendas = keys[config.num_players :]

    state.deck = [uid for uid in range(len(state.cards))]
    rng.shuffle(state.deck)
    for _ in range(config.starting_hand):
        for p in range(config.num_players):
            draw(state, p, rng)
    state.current = rng.randrange(config.num_players)
    return state


def play_game(
    config: Config,
    seed: int,
    bot_factory: Callable[[str, int, random.Random], "object"],
    *,
    game_id: int = 0,
    trace: bool = False,
    keep_state: bool = False,
) -> GameResult:
    rng = random.Random(seed)
    tiers = list(config.players)
    if config.shuffle_seats:
        rng.shuffle(tiers)
    state = setup_game(config, rng, trace=trace)
    bots = [bot_factory(tier, seat, rng) for seat, tier in enumerate(tiers)]
    watching = any(getattr(b, "observes", False) for b in bots)

    timeout = False
    while True:
        if state.turn >= config.max_turns:
            timeout = True
            break

        player = state.current
        if state.skip_next[player]:
            state.skip_next[player] = False
            state.bump("turns_skipped")
            state.note(f"P{player} skips their turn")
            state.turn += 1
            state.current = (state.current + 1) % config.num_players
            continue

        state.turn += 1
        actions = legal_actions(state, player)
        before = progress_vector(state) if watching else None
        action = bots[player].choose(state, player, actions)
        apply_action(state, player, action, rng)
        if watching:
            after = progress_vector(state)
            for bot in bots:
                if getattr(bot, "observes", False):
                    bot.observe(player, before, after)

        winners = check_winners(state)
        if winners:
            state.winners = winners
            for p in winners:
                state.revealed[p] = True
            break

        draw(state, player, rng)
        state.current = (state.current + 1) % config.num_players

    return GameResult(
        game_id=game_id,
        seed=seed,
        turns=state.turn,
        rounds=(state.turn + config.num_players - 1) // config.num_players,
        timeout=timeout,
        winners=list(state.winners),
        tiers=tiers,
        agendas=list(state.agendas),
        board=state.board_summary(),
        counts=count_board(state),
        stats=dict(state.stats),
        reshuffles=state.reshuffles,
        final_state=state if keep_state else None,
    )
