"""The browser's way into a game: JSON strings in, JSON strings out.

The web front end runs this package under Pyodide in a Web Worker and talks to
one `Table`. Strings keep the boundary simple -- no Python object ever leaks
into JavaScript -- and make every message easy to log and test.

Each call returns a list of *updates*, one per turn played, so the page can
show the bots moving one at a time at whatever pace it likes:

    {"seat": 2,                 # whose eyes `view` is through (-1: nobody's)
     "view": {...},             # session.view(seat)
     "log": ["[t4] P1 ..."],    # log lines new since the previous update
     "actor": 1,                # whose move this update shows (-1: nobody's yet)
     "action": {...} | null,    # the move itself -- all of it face up on the table
     "prompt": {...} | null,    # the question waiting on a human, if any
     "result": {...} | null}    # set once the game is over

The last update of a call is the one that stopped it: a prompt, or the end.
"""

from __future__ import annotations

import json
import random
from typing import Optional

from .agendas import AGENDAS
from .bots import BOT_TIERS
from .logsink import csv_text, row
from .session import HUMAN, OVER, GameSession, Prompt, action_json
from .state import Config

PLAYER_TYPES = (HUMAN, *BOT_TIERS)
MIN_PLAYERS = 2
#: One agenda each, so the table can be no bigger than the agenda pool.
MAX_PLAYERS = len(AGENDAS)


class Table:
    def __init__(self) -> None:
        self.session: Optional[GameSession] = None
        self._sent = 0  # log lines already sent

    # -- calls from the page ------------------------------------------------
    def new_game(self, request: str) -> str:
        """Deal a game. `{"players": ["human", "naive", ...], "seed": 7}`."""

        data = json.loads(request)
        players = tuple(data.get("players") or (HUMAN, "naive", "greedy", "strategic"))
        unknown = [p for p in players if p not in PLAYER_TYPES]
        if unknown:
            raise ValueError(f"unknown player type(s): {', '.join(unknown)}")
        if not MIN_PLAYERS <= len(players) <= MAX_PLAYERS:
            raise ValueError(f"a table seats {MIN_PLAYERS} to {MAX_PLAYERS} players")
        seed = data.get("seed")
        if seed is None:
            seed = random.randrange(2**31)
        self.session = GameSession(Config(players=players), int(seed))
        self._sent = 0
        # The table as dealt comes first, before anyone has moved: the page
        # shows each person their agenda there and waits for them to begin.
        return self._play_on([self._update(None)], None)

    def answer(self, choice: int) -> str:
        """Answer the waiting prompt: an action index, or a card uid mid-card."""

        prompt = self._live().answer(int(choice), advance=False)
        # The first update shows the answer itself landing on the board.
        return self._play_on([self._update(prompt)], prompt)

    def load(self, record: str) -> str:
        """Pick up a saved game (`record()`) where it stopped."""

        self.session = GameSession.replay(json.loads(record))
        self._sent = 0
        prompt = self.session.prompt or self.session.advance()
        return json.dumps([self._update(prompt)])

    def record(self) -> str:
        return json.dumps(self._live().record())

    def export(self, records: str) -> str:
        """Finished games as the CSV `python -m succession analyze` reads.

        Each record is replayed and logged by the simulator's own code, so a
        game played in the browser is a row like any batch run's. Unfinished
        records are skipped.
        """

        rows, width = [], 0
        for record in json.loads(records):
            session = GameSession.replay(record, trace=False)
            if not session.over:
                continue
            rows.append(row(session.result(game_id=len(rows)), session.config))
            width = max(width, session.config.num_players)
        return csv_text(rows, width)

    # -- plumbing -----------------------------------------------------------
    def _live(self) -> GameSession:
        if self.session is None:
            raise ValueError("no game has been dealt")
        return self.session

    def _play_on(self, updates: list, prompt: Optional[Prompt]) -> str:
        """Step the game, one update per turn, until someone must decide."""

        while prompt is None:
            prompt = self._live().step()
            updates.append(self._update(prompt))
        return json.dumps(updates)

    def _update(self, prompt: Optional[Prompt]) -> dict:
        session = self._live()
        if prompt is not None and prompt.kind != OVER:
            seat = prompt.player
        else:
            seat = session.humans[0] if session.humans else -1

        log = session.state.log
        new, self._sent = log[self._sent:], len(log)

        update = {
            "seat": seat,
            "view": session.view(seat),
            "log": new,
            "actor": session.last_actor,
            "action": (
                action_json(session.state, session.last_action, -1)
                if session.last_action is not None
                else None
            ),
            #: An event's effects, when this update is one (session.event_report).
            "event": session.last_event,
            "prompt": None,
            "result": None,
        }
        if prompt is not None and prompt.kind != OVER:
            update["prompt"] = session.prompt_json(prompt)
        if session.over:
            result = session.result()
            update["result"] = {
                "winners": result.winners,
                "timeout": result.timeout,
                "turns": result.turns,
                "record": session.record(),
            }
        return update


def options() -> str:
    """What the table setup screen may offer."""

    return json.dumps({
        "player_types": list(PLAYER_TYPES),
        "min_players": MIN_PLAYERS,
        "max_players": MAX_PLAYERS,
    })
