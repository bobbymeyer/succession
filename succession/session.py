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

from .actions import PLAY, Action, legal_actions
from .agendas import AGENDAS_BY_KEY, conditions, contributors, count_board, rules_for
from .bots import make_bot
from .cards import (
    EFFECT_DISCARD_ALL,
    EFFECT_DRAW_ALL,
    EFFECT_FREEZE_BOARD,
    EFFECT_FREEZE_INNER,
    EFFECT_PURGE,
    EFFECT_REDEAL,
    EFFECT_RESHUFFLE,
)
from .engine import GameResult, game_result, resolve_turn, setup_game, start_turn
from .enums import SEAT_ESTATE, SEATS, CardKind
from .state import Config, GameState

HUMAN = "human"

#: Prompt kinds.
TURN = "turn"            # pick one of `options`, the legal actions
COURTIER = "courtier"    # a purge: name one of `options`, courtier uids
DISCARD = "discard"      # a forced discard: throw away one of `options`, hand uids
OVER = "over"            # nothing left to decide

#: 2: Discard & Draw. A version-1 record was played before it, without the draw.
#: 3: the hand limit is checked at the end of the turn; earlier records capped
#: draws instead.
#: 4: events play when drawn, and the five majors are out of the deck; earlier
#: records held and played all ten.
RECORD_VERSION = 4


class NeedChoice(Exception):
    """Raised by a human seat asked to decide mid-card with no answer ready."""

    def __init__(self, kind: str, player: int, options: list[int], *, limit: bool = False) -> None:
        super().__init__(f"P{player} must choose a {kind}")
        self.kind = kind
        self.player = player
        self.options = options
        #: A discard down to the hand limit, rather than one a card asks for.
        self.limit = limit


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

    def pick_limit_discard(self, state: GameState, player: int, hand) -> int:
        return self._next(DISCARD, player, hand, limit=True)

    def _next(self, kind: str, player: int, options, *, limit: bool = False) -> int:
        if self.answers:
            return self.answers.pop(0)
        raise NeedChoice(kind, player, list(options), limit=limit)


@dataclass
class Prompt:
    """A question waiting on a human seat (or `OVER`, when there is none left)."""

    kind: str
    player: int = -1
    #: Legal `Action`s for a TURN; card uids for COURTIER and DISCARD.
    options: list = field(default_factory=list)
    #: The event card asking, for COURTIER and DISCARD.
    card: int = -1
    #: A DISCARD down to the hand limit as the turn ends (`card` is then -1).
    limit: bool = False


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
        self.seats = _Seats(seat_controllers(self.tiers, self.rng, bot_factory), self)
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
        #: What each event in the last update did to the table, in the order
        #: they began (see `event_report`): drawn at the start of a turn, or
        #: during it.
        self.last_events: list[dict] = []
        # Tables as they stood when each event still being resolved began.
        self._event_stack: list[tuple[int, "_Table"]] = []
        # The player whose turn has been opened (its draw done) but not taken.
        self._started: Optional[int] = None

        # The action being resolved when a human was asked mid-card (None for
        # the draw that opens a turn), the game as it stood just before it,
        # and the answers collected for it so far.
        self._resolving: Optional[tuple[int, Optional[Action]]] = None
        self._snapshot: Optional[tuple[GameState, object, list]] = None
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
        player = state.current
        if self._started is None:
            if state.turn >= self.config.max_turns:
                self.timeout = True
                return self._finish()
            prompt = self._start(player)
            if prompt is not None:
                return prompt
            # A skipped turn is over; one that opened with events shows them
            # before anything is played.
            if self._started is None or self.last_events:
                return None

        self._started = None
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
            self.state, rng_state, memories = copy.deepcopy(self._snapshot)
            self._restore_memories(memories)
            self.rng.setstate(rng_state)
            player, action = self._resolving
            if action is None:
                result = self._start(player, snapshot=False)
            else:
                result = self._resolve(player, action, snapshot=False)

        if result is not None or not advance:
            return result
        return self.advance()

    def _begin(self, player: int, action: Optional[Action], snapshot: bool) -> None:
        if snapshot and self.humans:
            self._snapshot = copy.deepcopy((self.state, self.rng.getstate(), self._memories()))
            self._answers = {}
        self._resolving = (player, action)
        self.last_actor = player
        self.last_action = action
        self.last_events = []
        self._event_stack = []
        for seat in self.humans:
            self.seats[seat].answers = list(self._answers.get(seat, ()))

    def _settled(self) -> None:
        self._resolving = None
        self._snapshot = None
        self._answers = {}

    def _asked(self, need: NeedChoice, card: int) -> Prompt:
        # Leave the half-played board up so the human sees what they are
        # choosing against; `answer()` rewinds to the snapshot.
        if self.state.resolving_event >= 0:
            card = self.state.resolving_event
        card = -1 if need.limit else card
        self.prompt = Prompt(need.kind, need.player, need.options, card, limit=need.limit)
        # Only events that have finished are reported; the one asking is
        # reported once the answer lets it finish.
        self.last_events = [e for e in self.last_events if e]
        return self.prompt

    def _start(self, player: int, *, snapshot: bool = True) -> Optional[Prompt]:
        """Open a turn: its draw, and any event that draw sets off."""

        self._begin(player, None, snapshot)
        try:
            started = start_turn(self.state, self.rng, self.seats)
        except NeedChoice as need:
            return self._asked(need, -1)
        self._settled()
        self._started = player if started else None
        return None

    def _on_event(self, phase: str, state: GameState, player: int, uid: int) -> None:
        """The engine's report of an event drawn and played (`on_event`)."""

        if phase == "before":
            self.last_events.append({})
            self._event_stack.append((len(self.last_events) - 1, _Table(state, player, uid, in_hand=False)))
        else:
            slot, before = self._event_stack.pop()
            self.last_events[slot] = event_report(before, state, drawn=True)

    def _resolve(self, player: int, action: Action, *, snapshot: bool = True) -> Optional[Prompt]:
        self._begin(player, action, snapshot)
        event = (
            action.kind == PLAY and self.state.card(action.card).kind is CardKind.EVENT
        )
        before = _Table(self.state, player, action.card) if event else None

        try:
            over = resolve_turn(self.state, player, action, self.rng, self.seats)
        except NeedChoice as need:
            return self._asked(need, action.card)

        self._settled()
        if before is not None:
            # An event played from hand: the old rules, before events played
            # when drawn.
            self.last_events.insert(0, event_report(before, self.state))
        if over:
            self.over = True
            return self._finish()
        return None

    # A bot that watches the table (`observes`) remembers what it saw. The
    # replay after a human's mid-turn answer shows it the same action again,
    # so its memory is part of the snapshot too.
    def _memories(self) -> list:
        return [
            {k: v for k, v in vars(seat).items() if k != "rng"} if getattr(seat, "observes", False) else None
            for seat in self.seats
        ]

    def _restore_memories(self, memories: list) -> None:
        for seat, memory in zip(self.seats, memories):
            if memory is not None:
                vars(seat).update(memory)

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
        if version not in (1, 2, 3, RECORD_VERSION):
            raise ValueError(f"unsupported record version {version!r}")
        config = dict(record["config"])
        if version == 1:
            config.setdefault("discard_draws", False)
        if version in (1, 2):
            config.setdefault("hand_limit_at_end_of_turn", False)
        if version in (1, 2, 3):
            config.setdefault("events_on_draw", False)
            config.setdefault("event_tiers", ["minor", "major"])
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
            #: The asking event's one-line summary, to announce it by.
            "summary": EVENT_SUMMARY.get(state.card(prompt.card).name, "") if prompt.card >= 0 else "",
            #: Cards still to go, when discarding down to the hand limit.
            "over": len(state.hands[prompt.player]) - state.config.hand_limit if prompt.limit else 0,
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
#: One line under an event's name, for the table to read at a glance.
EVENT_SUMMARY = {
    "Quarantine": "The court is sealed: no seat changes hands for a round.",
    "Siege": "The city is shut in: nothing on the board moves for a round.",
    "Poisoning at the Feast": "Every player names a courtier to die, all at once. Each may survive the poison.",
    "Plague": "Every player names a courtier to die, all at once. Nobody is spared.",
    "Caravan": "Trade arrives: a card for every player.",
    "Treasure Fleet": "A fleet arrives: two cards for every player.",
    "Debasement of the Coinage": "The coin is worthless: every player discards a card, all at once.",
    "Famine": "The granaries are empty: every player discards two cards, all at once.",
    "Eclipse": "The sky turns over: the discard pile goes back into the deck.",
    "Meteor": "Everything turns over: every hand is shuffled in and dealt back out.",
}


class _Seats(list):
    """The seat controllers, as the engine's `deciders`, plus an ear for events."""

    def __init__(self, seats, session: "GameSession") -> None:
        super().__init__(seats)
        self._session = session

    def on_event(self, phase: str, state: GameState, player: int, uid: int) -> None:
        self._session._on_event(phase, state, player, uid)


class _Table:
    """The parts of the table an event can change, just before it resolves."""

    def __init__(self, state: GameState, player: int, card: int, *, in_hand: bool = True) -> None:
        self.player = player
        self.card = card
        self.card_json = card_json(state, card)
        # A played event leaves its player's hand as it is played; count it
        # gone. A drawn one was never in it.
        self.hands = [len(h) - (p == player and in_hand) for p, h in enumerate(state.hands)]
        self.in_play = {uid: card_json(state, uid) for uid in _in_play(state)}
        self.deck = len(state.deck)
        self.discard = len(state.discard)
        self.log = len(state.log)


def _in_play(state: GameState) -> list[int]:
    return [uid for uid in state.seats.values() if uid is not None] + list(state.outer)


def event_report(before: _Table, state: GameState, *, drawn: bool = False) -> dict:
    """What an event just did to the table, for a front end to announce.

    `effects` are lines in the log's own voice ("P2 draws 2"), each with a
    tone: "loss", "gain" or "neutral". `fallen` and `spared` are the
    courtiers a purge named, as they were; `discarded` the cards a forced
    discard threw away, face up on the discard pile for everyone.
    """

    card = state.card(before.card)
    n = state.config.num_players
    order = [(before.player + i) % n for i in range(n)]
    effects: list[dict] = []
    fallen: list[dict] = []
    spared: list[dict] = []
    discarded: list[dict] = []

    def say(text: str, tone: str = "neutral") -> None:
        effects.append({"text": text, "tone": tone})

    effect = card.effect
    if effect == EFFECT_FREEZE_INNER:
        say(f"The inner circle is sealed until P{before.player}'s next turn.")
    elif effect == EFFECT_FREEZE_BOARD:
        say(f"The whole board is sealed until P{before.player}'s next turn.")
    elif effect == EFFECT_PURGE:
        # Everyone named at once; then the named died, or rolled and lived.
        still = set(_in_play(state))
        by_name = {c["name"]: c for c in before.in_play.values()}
        for line in state.log[before.log:]:
            text = line.split("] ", 1)[-1]
            if " names " not in text:
                continue
            who, name = text.split(" names ", 1)
            victim = by_name.get(name)
            if victim is None:
                continue
            if victim["uid"] in still:
                say(f"{who} names {name}, who survives.", "gain")
                if victim not in spared:
                    spared.append(victim)
            else:
                say(f"{who} names {name}, who dies.", "loss")
                if victim not in fallen:
                    fallen.append(victim)
        if not effects:
            say("Nobody is in play to name.")
    elif effect == EFFECT_DRAW_ALL:
        for p in order:
            got = len(state.hands[p]) - before.hands[p]
            full = (
                not state.config.hand_limit_at_end_of_turn
                and len(state.hands[p]) >= state.config.hand_limit
                and got < card.amount
            )
            note = " (hand full)" if full else ""
            if got > 0:
                say(f"P{p} draws {got}{note}", "gain")
            else:
                say(f"P{p} draws nothing{note}", "neutral")
    elif effect == EFFECT_DISCARD_ALL:
        for p in order:
            lost = before.hands[p] - len(state.hands[p])
            if lost > 0:
                say(f"P{p} discards {lost}", "loss")
            else:
                say(f"P{p} has nothing to discard", "neutral")
        # The event itself goes on the pile after them.
        thrown = [uid for uid in state.discard[before.discard:] if uid != before.card]
        discarded = [card_json(state, uid) for uid in thrown]
    elif effect == EFFECT_RESHUFFLE:
        say(f"{before.discard} cards go back into the deck, which now holds {len(state.deck)}.")
    elif effect == EFFECT_REDEAL:
        say("Every hand goes into the deck and is dealt back out, each as big as it was.")

    return {
        "card": before.card_json,
        "player": before.player,
        #: Played the moment it was drawn, rather than from a hand.
        "drawn": drawn,
        "summary": EVENT_SUMMARY.get(card.name, ""),
        "effects": effects,
        "fallen": fallen,
        "spared": spared,
        "discarded": discarded,
    }


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
