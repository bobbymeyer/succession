"""Command-line runner: play N games, log them, and summarise the batch.

    python -m succession run --games 1000 --out results.csv --summary
    python -m succession run --games 1000 --out results.db --format sqlite
    python -m succession analyze results.csv
    python -m succession demo --seed 42
    python -m succession play --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Iterator

from .agendas import AGENDA_KEYS, AGENDAS
from .analysis import format_summary, summarize
from .bots import BOT_TIERS, make_bot
from .enums import FAMILIES, Estate
from .engine import GameResult, play_game
from .logsink import open_sink, read_rows, row
from .session import HUMAN, GameSession
from .state import Config
from .terminal import play

DEFAULT_PLAYERS = "naive,greedy,strategic,naive"
#: One person against one bot of each tier.
DEFAULT_TABLE = "human,naive,greedy,strategic"


def parse_preferred_estates(spec: str) -> tuple[tuple[str, str], ...]:
    """Parse ``amonides=church,argaian=military`` into a family->estate mapping."""

    if not spec:
        return ()
    families = {f.value.lower(): f.value for f in FAMILIES}
    estates = {e.value.lower(): e.value for e in Estate}
    pairs: list[tuple[str, str]] = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise SystemExit(f"--house-preferred-estates: expected family=estate, got {item!r}")
        family, estate = (part.strip().lower() for part in item.split("=", 1))
        if family not in families:
            raise SystemExit(f"unknown family {family!r} (have: {', '.join(sorted(families))})")
        if estate not in estates:
            raise SystemExit(f"unknown estate {estate!r} (have: {', '.join(sorted(estates))})")
        pairs.append((families[family], estates[estate]))
    return tuple(pairs)


def parse_dropped_agendas(spec: str) -> tuple[str, ...]:
    if not spec:
        return ()
    keys = []
    for item in spec.split(","):
        key = item.strip().lower().replace(" ", "_").replace("-", "_")
        if not key:
            continue
        if key not in AGENDA_KEYS:
            raise SystemExit(
                f"unknown agenda {key!r} (have: {', '.join(AGENDA_KEYS)})"
            )
        keys.append(key)
    return tuple(keys)


def build_config(args: argparse.Namespace, tiers=BOT_TIERS) -> Config:
    players = tuple(p.strip() for p in args.players.split(",") if p.strip())
    unknown = [p for p in players if p not in tiers]
    if unknown:
        raise SystemExit(f"unknown player type(s): {', '.join(unknown)} (have: {', '.join(sorted(tiers))})")
    if len(players) < 2:
        raise SystemExit("need at least two players")
    if len(players) > len(AGENDAS):
        raise SystemExit(
            f"cannot deal one agenda per player: at most {len(AGENDAS)} players"
        )
    return Config(
        players=players,
        starting_hand=args.starting_hand,
        hand_limit=args.hand_limit,
        max_turns=args.max_turns,
        shuffle_seats=not args.fixed_seats,
        outmaneuver_copies=args.outmaneuver_copies,
        removed_courtiers_return_to_deck=not args.removed_out_of_game,
        discard_draws=not args.discard_no_draw,
        defense_requires_matching_target=args.defense_matches_target,
        house_rising_requires_preferred_seat=not args.house_any_three,
        house_preferred_estates=parse_preferred_estates(args.house_preferred_estates),
        faith_seats=args.faith_seats,
        balance_seats=args.balance_seats,
        balance_barbarians=args.balance_barbarians,
        excluded_agendas=parse_dropped_agendas(args.drop_agendas),
    )


def _play(job: tuple[Config, int, int]) -> GameResult:
    config, game_id, seed = job
    return play_game(config, seed, make_bot, game_id=game_id)


def run_games(config: Config, games: int, base_seed: int, jobs: int) -> Iterator[GameResult]:
    rng = random.Random(base_seed)
    batch = [(config, i, rng.randrange(2**31)) for i in range(games)]
    if jobs <= 1:
        for job in batch:
            yield _play(job)
        return
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        yield from pool.map(_play, batch, chunksize=max(1, games // (jobs * 8) or 1))


def cmd_run(args: argparse.Namespace) -> int:
    config = build_config(args)
    out = Path(args.out)
    fmt = args.format or ("sqlite" if out.suffix in {".db", ".sqlite", ".sqlite3"} else "csv")
    sink = open_sink(out, config, fmt)
    rows = []
    started = time.perf_counter()
    try:
        for n, result in enumerate(run_games(config, args.games, args.seed, args.jobs), start=1):
            data = row(result, config)
            sink.write(data)
            rows.append(data)
            if args.progress and (n % args.progress == 0 or n == args.games):
                elapsed = time.perf_counter() - started
                print(
                    f"\r{n}/{args.games} games  {n / elapsed:6.1f} games/s",
                    end="",
                    file=sys.stderr,
                    flush=True,
                )
    finally:
        sink.close()
    if args.progress:
        print(file=sys.stderr)

    elapsed = time.perf_counter() - started
    if not args.quiet:
        print(f"wrote {len(rows)} games to {out} ({fmt}) in {elapsed:.1f}s")
    if args.summary:
        print(format_summary(summarize(rows)))
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    rows: list[dict] = []
    for path in args.path:
        rows.extend(read_rows(Path(path)))
    print(format_summary(summarize(rows)))
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    config = build_config(args)
    result = play_game(
        config, args.seed, make_bot, game_id=0, trace=True, keep_state=True
    )
    state = result.final_state
    for line in state.log:
        print(line)
    print()
    print(state.describe())
    print()
    for p, (tier, agenda) in enumerate(zip(result.tiers, result.agendas)):
        mark = " <- WINNER" if p in result.winners else ""
        print(f"P{p} {tier:<10} {agenda}{mark}")
    print(f"\nturns: {result.turns}  timeout: {result.timeout}")
    return 0


def cmd_play(args: argparse.Namespace) -> int:
    if args.replay:
        record = json.loads(Path(args.replay).read_text())
        session = GameSession.replay(record)
    else:
        config = build_config(args, tiers=(*BOT_TIERS, HUMAN))
        seed = args.seed if args.seed is not None else random.randrange(2**31)
        session = GameSession(config, seed)
    finished = play(session)
    if args.record:
        Path(args.record).write_text(json.dumps(session.record()) + "\n")
        print(f"\nwrote the game record to {args.record}")
    elif not finished:
        print(f"\n(seed {session.seed}; --record FILE saves a game to replay with --replay FILE)")
    return 0


def add_rules_arguments(parser: argparse.ArgumentParser, players: str = DEFAULT_PLAYERS) -> None:
    parser.add_argument("--players", default=players, help=f"player types, clockwise (default: {players})")
    parser.add_argument("--starting-hand", type=int, default=5)
    parser.add_argument("--hand-limit", type=int, default=7)
    parser.add_argument("--max-turns", type=int, default=600, help="player-turn cap before a game is logged as a timeout")
    parser.add_argument("--outmaneuver-copies", type=int, default=1)
    parser.add_argument("--fixed-seats", action="store_true", help="do not randomise which tier sits where")
    parser.add_argument("--discard-no-draw", action="store_true", help="a turn spent discarding does not draw a replacement (default: Discard & Draw)")
    parser.add_argument("--removed-out-of-game", action="store_true", help="killed courtiers never return (default: they may reshuffle back as a new person)")
    parser.add_argument("--defense-matches-target", action="store_true", help="an estate Defense may only protect a courtier of that estate")
    parser.add_argument("--balance-seats", type=int, default=6, help="seats that must be filled for Balance to count (default 6 of 7)")
    parser.add_argument("--balance-barbarians", type=int, default=2, help="barbarians Balance wants seated (default 2)")
    parser.add_argument("--drop-agendas", default="", metavar="KEYS", help="leave agendas out of the pool entirely, e.g. balance")
    parser.add_argument("--faith-seats", type=int, default=4, help="inner seats a faith must hold to win (default 4 of 7)")
    parser.add_argument("--house-any-three", action="store_true", help="drop the preferred-estate requirement: any three seats of a family win")
    parser.add_argument("--house-preferred-estates", default="", metavar="SPEC", help="override a family's own estate, e.g. mitreas=church (default: amonides=church, mitreas=merchant, argaian=military)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="succession", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="simulate games and log the results")
    run.add_argument("--games", type=int, default=100)
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--out", default="results.csv")
    run.add_argument("--format", choices=["csv", "sqlite"], default=None)
    run.add_argument("--jobs", type=int, default=1, help="worker processes")
    run.add_argument("--summary", action="store_true", help="print the batch analysis when done")
    run.add_argument("--progress", type=int, default=0, metavar="EVERY", help="print progress every N games")
    run.add_argument("--quiet", action="store_true")
    add_rules_arguments(run)
    run.set_defaults(func=cmd_run)

    analyze = sub.add_parser(
        "analyze", help="summarise one or more previously written logs"
    )
    analyze.add_argument(
        "path", nargs="+", help="log files to pool (CSV or SQLite)"
    )
    analyze.set_defaults(func=cmd_analyze)

    demo = sub.add_parser("demo", help="play one traced game and print it")
    demo.add_argument("--seed", type=int, default=0)
    add_rules_arguments(demo)
    demo.set_defaults(func=cmd_demo)

    play_ = sub.add_parser("play", help="take a seat at the table against the bots")
    play_.add_argument("--seed", type=int, default=None, help="deal a particular game (default: a random one)")
    play_.add_argument("--record", metavar="FILE", help="save the game, decision by decision, when it ends or you quit")
    play_.add_argument("--replay", metavar="FILE", help="replay a saved game to where it stopped, then carry on playing")
    add_rules_arguments(play_, players=DEFAULT_TABLE)
    play_.set_defaults(func=cmd_play)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
