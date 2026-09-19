"""The three bot tiers.

* **Naive** picks a uniformly random legal action.
* **Greedy** looks one ply ahead and maximises progress on its own hidden
  agenda, ignoring everyone else.
* **Strategic** maximises its own agenda *and* watches the whole agenda pool:
  it discounts actions that push any other agenda toward completion, weighting
  each rival agenda by how strongly the opponents' observed play suggests
  somebody holds it.

All three see only public information plus their own agenda. The strategic
bot's belief model is built purely from what it can observe: which agendas each
opponent's actions advanced.
"""

from __future__ import annotations

import random
from typing import Optional, Sequence

from .actions import DISCARD, MOVE, PASS, PLAY, Action
from .agendas import (
    AGENDA_KEYS,
    AGENDAS,
    AGENDAS_BY_KEY,
    count_board,
    progress_counts,
    rules_for,
    satisfied_counts,
)
from .enums import CardKind
from .engine import simulate
from .state import GameState

#: How many candidate actions a thinking bot evaluates per turn. Target-heavy
#: cards (removals, mutations, events) can generate dozens of near-identical
#: actions; pruning keeps a game fast without changing the tier's character.
CANDIDATE_LIMIT = 22
PER_CARD_LIMIT = 4

#: How hard the strategic bot leans on suppressing other agendas.
THREAT_WEIGHT = 0.7
#: Prior odds that an arbitrary rival agenda is actually in an opponent's hand
#: (three of the six agendas a player does not hold are dealt out).
BASE_BELIEF = 0.5


def agenda_pool(state: GameState) -> list:
    """Every agenda in this game -- dealt or in the fog, but not excluded ones.

    Which agendas are *in play* is public (it is the deck); which player holds
    which is not.
    """

    return [
        AGENDAS_BY_KEY[k] for k in (*state.agendas, *state.unused_agendas)
    ]


def _is_pivot(state: GameState, action: Action) -> bool:
    return (
        action.kind == PLAY
        and action.card >= 0
        and state.card(action.card).kind is CardKind.PIVOT
    )


class Bot:
    """Base class. Bots are per-seat and may keep state between turns."""

    tier = "base"
    observes = False

    def __init__(self, seat: int, rng: random.Random, config=None) -> None:
        self.seat = seat
        self.rng = rng

    def choose(self, state: GameState, player: int, actions: Sequence[Action]) -> Action:
        raise NotImplementedError

    def observe(self, actor: int, before: dict[str, float], after: dict[str, float]) -> None:
        """Called after every action with the agenda-progress delta it caused."""


class NaiveBot(Bot):
    """Tier 1: any legal move, chosen at random."""

    tier = "naive"

    def choose(self, state: GameState, player: int, actions: Sequence[Action]) -> Action:
        return self.rng.choice(list(actions))


class ThinkingBot(Bot):
    """Shared machinery for the two tiers that actually evaluate the board."""

    tier = "thinking"

    def candidates(self, state: GameState, actions: Sequence[Action]) -> list[Action]:
        """Prune to a manageable, representative set of candidate actions."""

        by_card: dict[int, list[Action]] = {}
        moves: list[Action] = []
        discards: list[Action] = []
        for action in actions:
            if action.kind == MOVE:
                moves.append(action)
            elif action.kind == DISCARD:
                discards.append(action)
            elif action.kind == PASS:
                return [action]
            else:
                by_card.setdefault(action.card, []).append(action)

        inner = set(state.inner_uids())
        picked: list[Action] = []
        for group in by_card.values():
            if len(group) <= PER_CARD_LIMIT:
                picked.extend(group)
                continue
            # Inner-circle targets change the board that agendas are scored on,
            # so they are always worth a look; fill the rest at random.
            hot = [a for a in group if a.courtier in inner]
            cold = [a for a in group if a.courtier not in inner]
            self.rng.shuffle(hot)
            self.rng.shuffle(cold)
            picked.extend((hot + cold)[:PER_CARD_LIMIT])

        picked.extend(moves)
        if discards:
            self.rng.shuffle(discards)
            picked.extend(discards[: max(2, PER_CARD_LIMIT)])
        if len(picked) > CANDIDATE_LIMIT:
            self.rng.shuffle(picked)
            forced = [a for a in picked if a.kind == MOVE][:4]
            picked = forced + [a for a in picked if a not in forced]
            picked = picked[:CANDIDATE_LIMIT]
        return picked or list(actions)

    # -- scoring ------------------------------------------------------------
    def my_agenda(self, state: GameState, player: int):
        return AGENDAS_BY_KEY[state.agendas[player]]

    def structural_bonus(self, state: GameState, player: int, action: Action) -> float:
        """Small tie-breakers that keep a bot from idling when nothing scores."""

        if action.kind == MOVE:
            return 0.004
        if action.kind == DISCARD:
            card = state.card(action.card)
            if card.is_courtier and self.is_useful_courtier(state, player, action.card):
                return -0.010  # do not throw away courtiers our agenda wants
            return 0.001
        if action.kind == PLAY and state.card(action.card).is_courtier:
            return 0.002
        return 0.0

    def is_useful_courtier(self, state: GameState, player: int, uid: int) -> bool:
        agenda = self.my_agenda(state, player)
        c = state.cstate[uid]
        if agenda.kind == "house":
            return c.family.value == agenda.param
        if agenda.kind == "faith":
            return c.faith.value == agenda.param
        if agenda.kind == "conquest":
            return c.origin.value == "Barbarian" or c.estate.value == "Military"
        return True

    def pivot_score(self, state: GameState, player: int, current: float) -> float:
        """Expected value of swapping to a random unused agenda."""

        if not state.unused_agendas:
            return -1.0
        counts = count_board(state)
        rules = rules_for(state)
        expected = sum(
            progress_counts(counts, AGENDAS_BY_KEY[k], rules)
            for k in state.unused_agendas
        ) / len(state.unused_agendas)
        # Only worth the turn if the grass is meaningfully greener.
        return current + (expected - current) - 0.05

    def choose(self, state: GameState, player: int, actions: Sequence[Action]) -> Action:
        agenda = self.my_agenda(state, player)
        current = progress_counts(count_board(state), agenda, rules_for(state))

        best: Optional[Action] = None
        best_score = float("-inf")
        for action in self.candidates(state, actions):
            if _is_pivot(state, action):
                # A pivot's new agenda is drawn at random, so lookahead cannot
                # see it; score its expected value instead.
                score = self.pivot_score(state, player, current)
            else:
                after = simulate(state, player, action)
                score = self.score(after, state, player, action)
            score += self.structural_bonus(state, player, action)
            score += self.rng.random() * 1e-6  # break ties without bias
            if score > best_score:
                best_score, best = score, action
        return best if best is not None else self.rng.choice(list(actions))

    def score(self, after: GameState, before: GameState, player: int, action: Action) -> float:
        raise NotImplementedError


class GreedyBot(ThinkingBot):
    """Tier 2: advance my own agenda, and nothing else."""

    tier = "greedy"

    def score(self, after: GameState, before: GameState, player: int, action: Action) -> float:
        agenda = self.my_agenda(before, player)
        rules = rules_for(before)
        counts = count_board(after)
        if satisfied_counts(counts, agenda, rules):
            return 100.0  # this action wins the game outright
        return progress_counts(counts, agenda, rules)


class StrategicBot(ThinkingBot):
    """Tier 3: advance my agenda while suppressing everyone else's.

    Keeps a belief score per opponent per agenda, accumulated from the progress
    each of their actions produced, and weights the threat term by it.
    """

    tier = "strategic"
    observes = True

    def __init__(self, seat: int, rng: random.Random, config=None) -> None:
        super().__init__(seat, rng, config)
        self.belief: dict[int, dict[str, float]] = {}

    def observe(self, actor: int, before: dict[str, float], after: dict[str, float]) -> None:
        if actor == self.seat:
            return
        beliefs = self.belief.setdefault(actor, {k: 0.0 for k in AGENDA_KEYS})
        for key, value in after.items():
            gain = value - before[key]
            if gain > 0:
                beliefs[key] += gain
        # Decay keeps early noise from dominating a long game.
        for key in beliefs:
            beliefs[key] *= 0.98

    def threat_weight(self, key: str) -> float:
        """0.5 (no evidence) .. 1.0 (an opponent is clearly chasing this)."""

        best = 0.0
        for beliefs in self.belief.values():
            total = sum(beliefs.values())
            if total <= 0:
                continue
            best = max(best, beliefs[key] / total)
        return BASE_BELIEF + (1.0 - BASE_BELIEF) * min(1.0, best * len(AGENDA_KEYS) / 2.0)

    def score(self, after: GameState, before: GameState, player: int, action: Action) -> float:
        mine = before.agendas[player]
        agenda = AGENDAS_BY_KEY[mine]
        rules = rules_for(before)
        counts = count_board(after)

        if satisfied_counts(counts, agenda, rules):
            return 100.0

        own = progress_counts(counts, agenda, rules)
        threat = 0.0
        for rival in agenda_pool(before):
            if rival.key == mine:
                continue
            rival_progress = progress_counts(counts, rival, rules)
            weight = self.threat_weight(rival.key)
            if rival_progress >= 1.0:
                # Handing an opponent the win is the worst thing we can do.
                threat = max(threat, 10.0 * weight)
            else:
                threat = max(threat, weight * rival_progress)
        return own - THREAT_WEIGHT * threat

    def structural_bonus(self, state: GameState, player: int, action: Action) -> float:
        bonus = super().structural_bonus(state, player, action)
        if action.kind == PLAY and action.player >= 0:
            card = state.card(action.card)
            if card.kind is CardKind.OUTMANEUVER:
                # Stall whichever opponent looks closest to their agenda.
                beliefs = self.belief.get(action.player, {})
                total = sum(beliefs.values()) or 1.0
                counts = count_board(state)
                rules = rules_for(state)
                lead = max(
                    (
                        beliefs.get(a.key, 0.0) / total * progress_counts(counts, a, rules)
                        for a in agenda_pool(state)
                        if a.key != state.agendas[player]
                    ),
                    default=0.0,
                )
                bonus += 0.02 + 0.5 * lead
        return bonus


BOT_TIERS: dict[str, type[Bot]] = {
    "naive": NaiveBot,
    "greedy": GreedyBot,
    "strategic": StrategicBot,
}


def make_bot(tier: str, seat: int, rng: random.Random) -> Bot:
    try:
        cls = BOT_TIERS[tier]
    except KeyError:  # pragma: no cover - guarded by the CLI
        raise ValueError(f"unknown bot tier {tier!r}; choose from {sorted(BOT_TIERS)}") from None
    return cls(seat, rng)
