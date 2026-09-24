"""Find a friendly seed for a new player's first game.

A seed fixes the whole deal: where everyone sits, the agendas, every hand,
and the bots' dice. The page deals a new player's first game (the default
table, nothing played yet in this browser) from one fixed seed, so it may as
well be a kind one. This script looks for it.

A seed is friendly when the human
  * moves first or second,
  * holds an agenda a newcomer can read -- Faith Ascendant or House Rising --
  * starts with courtiers for it in hand,
and, with a bot sitting in for the human, the human's seat goes on to win
however well the stand-in plays: the naive bot (a beginner), the greedy bot
and the strategic bot each play it once, and the more of them win, and the
sooner, the better.

    python tools/friendly_seed.py --seeds 4000 --top 10

The seed chosen is FIRST_GAME_SEED in web/src/firstGame.ts.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from succession.agendas import AGENDAS_BY_KEY, FAITH_ASCENDANT, HOUSE_RISING  # noqa: E402
from succession.bots import make_bot  # noqa: E402
from succession.engine import play_game  # noqa: E402
from succession.session import HUMAN, GameSession  # noqa: E402
from succession.state import Config  # noqa: E402

#: The page's default table: you and one of each bot.
TABLE = (HUMAN, "naive", "greedy", "strategic")
STAND_INS = ("naive", "greedy", "strategic")


def opening(seed: int) -> dict:
    """The deal as the human sees it, before anyone moves."""

    session = GameSession(Config(players=TABLE), seed)
    me = session.humans[0]
    state = session.state
    agenda = AGENDAS_BY_KEY[state.agendas[me]]
    n = state.config.num_players
    helpful = 0
    for uid in state.hands[me]:
        card = state.card(uid)
        if card.is_courtier:
            c = state.cstate[uid]
            if agenda.kind == FAITH_ASCENDANT and c.faith.value == agenda.param:
                helpful += 1
            elif agenda.kind == HOUSE_RISING and c.family.value == agenda.param:
                helpful += 1
    return {
        "seat": me,
        "position": (me - state.current) % n,  # 0: moves first
        "agenda": agenda,
        "helpful": helpful,
    }


def stand_in_games(seed: int, seat: int) -> list[tuple[str, bool, int]]:
    """The same deal with each bot in the human's chair: (bot, won, turns)."""

    out = []
    for tier in STAND_INS:
        def factory(t, s, rng, tier=tier):
            return make_bot(tier if t == HUMAN else t, s, rng)

        result = play_game(Config(players=TABLE), seed, factory)
        out.append((tier, seat in result.winners and not result.timeout, result.turns))
    return out


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=4000, help="seeds to try, from 0")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args(argv)

    found = []
    for seed in range(args.seeds):
        o = opening(seed)
        if o["position"] > 1 or o["agenda"].kind not in (FAITH_ASCENDANT, HOUSE_RISING) or o["helpful"] < 2:
            continue
        games = stand_in_games(seed, o["seat"])
        wins = sum(won for _, won, _ in games)
        if wins < 2:
            continue
        turns = sum(t for _, won, t in games if won) / wins
        found.append((wins, o["helpful"], -turns, seed, o, games))

    found.sort(reverse=True)
    for wins, helpful, turns, seed, o, games in found[: args.top]:
        played = ", ".join(f"{t} {'won' if w else 'lost'} in {n}" for t, w, n in games)
        print(
            f"seed {seed}: {o['agenda'].name}, moves {'first' if o['position'] == 0 else 'second'}, "
            f"{helpful} courtiers for it in hand; {played}"
        )


if __name__ == "__main__":
    main()
