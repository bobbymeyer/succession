"""One game at a time, with people at the table: the engine a front end drives.

`play_game()` runs a game straight through because every seat is a bot. A
person cannot be called like a bot -- a browser or a terminal has to be handed
a question and come back later with the answer -- so `GameSession` runs the
same turn loop (`start_turn` / `resolve_turn`) but stops whenever a human seat
has to decide something, and resumes when `answer()` is called:

    session = GameSession(Config(players=("human", "naive", "greedy", "strategic")), seed=7)
    prompt = session.advance()          # bots play until a human must decide
    while prompt.kind != OVER:
        ...                             # show session.view(prompt.player), prompt.options
        prompt = session.answer(choice)

A human is asked two kinds of thing. On their own turn, which legal action to
take. And mid-card, when an event asks the whole table: a purge makes every
player name a victim, a famine makes every player discard. Those arrive in the
middle of `apply_action()`, possibly on a bot's turn, with the card already
half resolved. Rather than turn the engine inside out to pause there, the
session snapshots the game before every action, lets the human's stand-in
raise `NeedChoice` when asked, and on the answer restores the snapshot and
resolves the action again with the answer ready. The random generator is part
of the snapshot, so every save roll and every bot's pick comes out the same the
second time.

Everything a human decides is kept in `decisions`, so `record()` plus
`replay()` rebuild a game exactly -- a bug report is one small JSON object.

`view()` is the only picture of the game a front end should get: the board, the
viewer's own hand and agenda, and nothing about anyone else's that the table
could not see.
"""

from __future__ import annotations

import copy
import random
from dataclasses import asdict, dataclass, field, fields
from typing import Callable, Optional

from .actions import Action, legal_actions
from .agendas import AGENDAS_BY_KEY, conditions, contributors, count_board, rules_for
from .bots import make_bot
from .engine import GameResult, game_result, resolve_turn, setup_game, start_turn
from .enums import SEAT_ESTATE, SEATS
from .state import Config, GameState

HUMAN = "human"

#: Prompt kinds.
TURN = "turn"            # pick one of `options`, the legal actions
COURTIER = "courtier"    # a purge: name one of `options`, courtier uids
DISCARD = "discard"      # a forced discard: throw away one of `options`, hand uids
OVER = "over"            # nothing left to decide

#: 2: Discard & Draw. A version-1 record was played before it, without the draw.
RECORD_VERSION = 2


class NeedChoice(Exception):
    """Raised by a human seat asked to decide mid-card with no answer ready."""

    def __init__(self, kind: str, player: int, options: list[int]) -> None:
        super().__init__(f"P{player} must choose a {kind}")
        self.kind = kind
        self.player = player
        self.options = options


class HumanSeat:
    """Stands in for a person wherever the engine expects a bot.

    It never picks anything itself. Answers the session already has are handed
    over in order; past the end of them it raises `NeedChoice`.
    """

    tier = HUMAN
    observes = False

    def __init__(self, seat: int) -> None:
        self.seat = seat
        self.answers: list[int] = []

    def pick_courtier(self, state: GameState, player: int, candidates) -> int:
        return self._next(COURTIER, player, candidates)

    def pick_discard(self, state: GameState, player: int, hand) -> int:
        return self._next(DISCARD, player, hand)

    def _next(self, kind: str, player: int, options) -> int:
        if self.answers:
            return self.answers.pop(0)
        raise NeedChoice(kind, player, list(options))


@dataclass
class Prompt:
    """A question waiting on a human seat (or `OVER`, when there is none left)."""

    kind: str
    player: int = -1
    #: Legal `Action`s for a TURN; card uids for COURTIER and DISCARD.
    options: list = field(default_factory=list)
    #: The event card asking, for COURTIER and DISCARD.
    card: int = -1


def seat_controllers(
    tiers: list[str], rng: random.Random, bot_factory: Callable = make_bot
) -> list:
    return [
        HumanSeat(seat) if tier == HUMAN else bot_factory(tier, seat, rng)
        for seat, tier in enumerate(tiers)
    ]


class GameSession:
    def __init__(
        self,
        config: Config,
        seed: int,
        *,
        bot_factory: Callable = make_bot,
        trace: bool = True,
    ) -> None:
        self.config = config
        self.seed = seed
        # The same setup as play_game, draw for draw, so the same seed deals
        # the same game.
        self.rng = random.Random(seed)
        self.tiers = list(config.players)
        if config.shuffle_seats:
            self.rng.shuffle(self.tiers)
        self.state = setup_game(config, self.rng, trace=trace)
        self.seats = seat_controllers(self.tiers, self.rng, bot_factory)
        self.humans = [s.seat for s in self.seats if isinstance(s, HumanSeat)]

        #: Every human answer so far, in order: an index into the legal actions
        #: on a TURN, a card uid on a COURTIER or DISCARD.
        self.decisions: list[int] = []
        self.timeout = False
        self.over = False
        self.prompt: Optional[Prompt] = None
        #: Whose turn was played last (or skipped), and the action they took
        #: (None for a skipped turn), for a front end to animate.
        self.last_actor = -1
        self.last_action: Optional[Action] = None

        # The action being resolved when a human was asked mid-card, the game
        # as it stood just before it, and the answers collected for it so far.
        self._resolving: Optional[tuple[int, Action]] = None
        self._snapshot: Optional[tuple[GameState, object]] = None
        self._answers: dict[int, list[int]] = {}

    # -- driving the game ---------------------------------------------------
    def step(self) -> Optional[Prompt]:
        """Play one turn if no human is being waited on.

        Returns the prompt a human must answer, `OVER`, or None when a bot (or
        a skipped turn) moved and play can simply continue. A front end that
        wants to show the bots moving one at a time calls this in a loop.
        """

        if self.prompt is not None:
            return self.prompt
        if self.over:
            return self._finish()

        state = self.state
        if state.turn >= self.config.max_turns:
            self.timeout = True
            return self._finish()

        player = state.current
        if not start_turn(state, self.rng):
            self.last_actor = player
            self.last_action = None
            return None
        actions = legal_actions(state, player)
        seat = self.seats[player]
        if isinstance(seat, HumanSeat):
            self.prompt = Prompt(TURN, player, actions)
            return self.prompt
        return self._resolve(player, seat.choose(state, player, actions))

    def advance(self) -> Prompt:
        """Play bot turns until a human has to decide something, or it's over."""

        while True:
            prompt = self.step()
            if prompt is not None:
                return prompt

    def answer(self, choice: int, *, advance: bool = True) -> Optional[Prompt]:
        """Answer the waiting prompt and play on to the next one.

        `choice` is an index into `prompt.options` for a TURN, and one of the
        card uids in `prompt.options` for a COURTIER or DISCARD. With
        `advance=False` only the answered action is played, as `step()` would,
        and None means play can continue.
        """

        prompt = self.prompt
        if prompt is None or prompt.kind == OVER:
            raise ValueError("no question is waiting for an answer")

        if prompt.kind == TURN:
            if not 0 <= choice < len(prompt.options):
                raise ValueError(
                    f"choice {choice} is out of range: {len(prompt.options)} legal actions"
                )
            self.decisions.append(choice)
            self.prompt = None
            result = self._resolve(prompt.player, prompt.options[choice])
        else:
            if choice not in prompt.options:
                raise ValueError(f"card {choice} is not one of the choices offered")
            self.decisions.append(choice)
            self._answers.setdefault(prompt.player, []).append(choice)
            self.prompt = None
            # Back to the moment before the card was played, and play it again
            # with this answer (and any earlier ones) ready.
            self.state, rng_state = copy.deepcopy(self._snapshot)
            self.rng.setstate(rng_state)
            player, action = self._resolving
            result = self._resolve(player, action, snapshot=False)

        if result is not None or not advance:
            return result
        return self.advance()

    def _resolve(self, player: int, action: Action, *, snapshot: bool = True) -> Optional[Prompt]:
        if snapshot and self.humans:
            self._snapshot = copy.deepcopy((self.state, self.rng.getstate()))
            self._answers = {}
        self._resolving = (player, action)
        self.last_actor = player
        self.last_action = action
        for seat in self.humans:
            self.seats[seat].answers = list(self._answers.get(seat, ()))

        try:
            over = resolve_turn(self.state, player, action, self.rng, self.seats)
        except NeedChoice as need:
            # Leave the half-played board up so the human sees what they are
            # choosing against; `answer()` rewinds to the snapshot.
            self.prompt = Prompt(need.kind, need.player, need.options, action.card)
            return self.prompt

        self._resolving = None
        self._snapshot = None
        self._answers = {}
        if over:
            self.over = True
            return self._finish()
        return None

    def _finish(self) -> Prompt:
        self.over = True
        self.prompt = Prompt(OVER)
        return self.prompt

    # -- results and records ------------------------------------------------
    def result(self, game_id: int = 0) -> GameResult:
        if not self.over:
            raise ValueError("the game is still being played")
        return game_result(
            self.state, self.tiers, game_id=game_id, seed=self.seed, timeout=self.timeout
        )

    def record(self) -> dict:
        """Everything needed to play this game again, decision for decision."""

        return {
            "version": RECORD_VERSION,
            "seed": self.seed,
            "config": asdict(self.config),
            "decisions": list(self.decisions),
        }

    @classmethod
    def replay(cls, record: dict, *, bot_factory: Callable = make_bot, trace: bool = True) -> "GameSession":
        """Rebuild a game from `record()`, stopped where the record ends."""

        version = record.get("version")
        if version not in (1, RECORD_VERSION):
            raise ValueError(f"unsupported record version {version!r}")
        config = dict(record["config"])
        if version == 1:
            config.setdefault("discard_draws", False)
        session = cls(
            config_from_json(config),
            record["seed"],
            bot_factory=bot_factory,
            trace=trace,
        )
        session.advance()
        for choice in record["decisions"]:
            session.answer(choice)
        return session

    # -- what a seat can see ------------------------------------------------
    def view(self, player: int) -> dict:
        return view(self.state, player, self.tiers, over=self.over)

    def prompt_json(self, prompt: Optional[Prompt] = None) -> dict:
        prompt = prompt or self.prompt or Prompt(OVER)
        state = self.state
        if prompt.kind == TURN:
            options = [action_json(state, a, i) for i, a in enumerate(prompt.options)]
        else:
            options = [card_json(state, uid) for uid in prompt.options]
        return {
            "kind": prompt.kind,
            "player": prompt.player,
            "options": options,
            "card": card_json(state, prompt.card) if prompt.card >= 0 else None,
        }


def config_from_json(data: dict) -> Config:
    """Invert `asdict(config)`: JSON gives lists where Config wants tuples."""

    def tuples(value):
        if isinstance(value, list):
            return tuple(tuples(v) for v in value)
        return value

    known = {f.name for f in fields(Config)}
    return Config(**{k: tuples(v) for k, v in data.items() if k in known})


# --- the public picture of the game -----------------------------------------
def card_json(state: GameState, uid: int) -> dict:
    card = state.card(uid)
    data = {
        "uid": uid,
        "name": card.name,
        "kind": card.kind.value,
        "estate": card.estate.value if card.estate is not None else None,
    }
    if card.is_courtier:
        live = state.cstate[uid]
        printed = state.base(uid)
        attributes = ("estate", "faith", "family", "origin")
        data.update({a: getattr(live, a).value for a in attributes})
        #: Attributes that differ from the printed card -- by mutation or strip.
        data["changed"] = [a for a in attributes if getattr(live, a) != getattr(printed, a)]
        #: Attributes whose one mutation has been spent.
        data["mutated"] = [a for a in attributes if live.mutated(a)]
        defense = state.defenses.get(uid)
        data["defense"] = card_json(state, defense) if defense is not None else None
    return data


def action_json(state: GameState, action: Action, index: int) -> dict:
    def uid(value: int) -> Optional[int]:
        return value if value >= 0 else None

    return {
        "index": index,
        "kind": action.kind,
        "card": uid(action.card),
        "courtier": uid(action.courtier),
        "seat": action.seat.value if action.seat is not None else None,
        "target_player": uid(action.player),
        "sacrifice": uid(action.sacrifice),
        "value": action.value or None,
        "text": action.describe(state),
    }


def view(state: GameState, player: int, tiers: list[str], *, over: bool = False) -> dict:
    """The game as seat `player` sees it. Pass -1 for a spectator's view.

    Hidden: every other hand, and every agenda not yet revealed. Once the game
    is over all agendas are shown.
    """

    counts, rules = count_board(state), rules_for(state)

    def agenda(p: int) -> Optional[dict]:
        if p != player and not state.revealed[p] and not over:
            return None
        a = AGENDAS_BY_KEY[state.agendas[p]]
        status = conditions(counts, a, rules)
        return {
            "key": a.key,
            "name": a.name,
            "met": all(c.met for c in status),
            #: Clause by clause: what the board has, what the agenda needs.
            "status": [
                {"label": c.label, "have": c.have, "need": c.need, "met": c.met, "waiting": c.waiting}
                for c in status
            ],
            #: The seated courtiers that count toward it.
            "seated": contributors(state, a),
        }

    seats = []
    for seat in SEATS:
        uid = state.seats[seat]
        seats.append({
            "seat": seat.value,
            "estate": SEAT_ESTATE[seat].value,
            "courtier": card_json(state, uid) if uid is not None else None,
        })

    return {
        "you": player,
        "turn": state.turn,
        "current": state.current,
        "over": over,
        "winners": list(state.winners),
        "players": [
            {
                "seat": p,
                "tier": tiers[p],
                "hand": len(state.hands[p]),
                "agenda": agenda(p),
                "skips_next_turn": state.skip_next[p],
            }
            for p in range(state.config.num_players)
        ],
        "hand": [card_json(state, uid) for uid in state.hands[player]] if player >= 0 else [],
        "seats": seats,
        "outer": [card_json(state, uid) for uid in state.outer],
        "deck": len(state.deck),
        "discard": len(state.discard),
        "discard_top": card_json(state, state.discard[-1]) if state.discard else None,
        "removed": len(state.removed),
        "frozen": {"inner": state.inner_frozen, "board": state.board_frozen},
    }


__all__ = [
    "COURTIER",
    "DISCARD",
    "GameSession",
    "HUMAN",
    "HumanSeat",
    "NeedChoice",
    "OVER",
    "Prompt",
    "TURN",
    "action_json",
    "card_json",
    "config_from_json",
    "view",
]
