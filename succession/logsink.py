"""Per-game result rows and the CSV / SQLite sinks that store them."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any

from .engine import GameResult
from .enums import SEATS, Faith, Family
from .state import Config

#: Stats counters promoted to their own column (everything else is dropped).
STAT_COLUMNS: tuple[str, ...] = (
    "moves",
    "turns_skipped",
    "courtiers_killed",
    "freezes_inner",
    "freezes_board",
    "cards_given",
    "cards_forced_out",
    "redeals",
    "courtiers_sacrificed",
    "defenses_triggered",
    "saves_made",
    "pivots",
    "played_courtier",
    "played_event",
    "played_promotion",
    "played_demotion",
    "played_removal",
    "played_defense",
    "played_strip",
    "played_mutation",
    "played_outmaneuver",
    "action_play",
    "action_move",
    "action_discard",
)


def _seat_column(seat) -> str:
    return "seat_" + seat.value.lower().replace(" ", "_").replace("-", "_")


def columns(config: Config) -> list[str]:
    cols = [
        "game_id",
        "seed",
        "turns",
        "rounds",
        "timeout",
        "num_winners",
        "double_win",
        "winning_agendas",
        "winning_tiers",
        "reshuffles",
    ]
    for p in range(config.num_players):
        cols += [f"p{p}_tier", f"p{p}_agenda", f"p{p}_won"]
    cols += [_seat_column(s) for s in SEATS]
    cols += [
        "inner_filled",
        "inner_barbarians",
        "inner_amonides",
        "inner_mitreas",
        "inner_argaian",
        "inner_old_gods",
        "inner_mystery_cults",
    ]
    cols += list(STAT_COLUMNS)
    return cols


def row(result: GameResult, config: Config) -> dict[str, Any]:
    """Flatten one finished game into a log row."""

    data: dict[str, Any] = {
        "game_id": result.game_id,
        "seed": result.seed,
        "turns": result.turns,
        "rounds": result.rounds,
        "timeout": int(result.timeout),
        "num_winners": len(result.winners),
        "double_win": int(len(result.winners) > 1),
        "winning_agendas": "|".join(result.winning_agendas),
        "winning_tiers": "|".join(result.winning_tiers),
        "reshuffles": result.reshuffles,
    }
    for p in range(config.num_players):
        data[f"p{p}_tier"] = result.tiers[p]
        data[f"p{p}_agenda"] = result.agendas[p]
        data[f"p{p}_won"] = int(p in result.winners)
    for seat in SEATS:
        data[_seat_column(seat)] = result.board[seat.value]

    counts = result.counts
    data["inner_filled"] = sum(1 for v in result.board.values() if v)
    data["inner_barbarians"] = counts.inner_barbarians
    data["inner_amonides"] = counts.inner_family.get(Family.AMONIDES.value, 0)
    data["inner_mitreas"] = counts.inner_family.get(Family.MITREAS.value, 0)
    data["inner_argaian"] = counts.inner_family.get(Family.ARGAIAN.value, 0)
    data["inner_old_gods"] = counts.inner_faith.get(Faith.OLD_GODS.value, 0)
    data["inner_mystery_cults"] = counts.inner_faith.get(Faith.MYSTERY_CULTS.value, 0)

    for key in STAT_COLUMNS:
        data[key] = result.stats.get(key, 0)
    return data


class CsvSink:
    def __init__(self, path: Path, config: Config) -> None:
        self.path = path
        self.cols = columns(config)
        self._fh = path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._fh, fieldnames=self.cols)
        self._writer.writeheader()

    def write(self, data: dict[str, Any]) -> None:
        self._writer.writerow(data)

    def close(self) -> None:
        self._fh.close()


class SqliteSink:
    def __init__(self, path: Path, config: Config) -> None:
        self.path = path
        self.cols = columns(config)
        self.conn = sqlite3.connect(path)
        text_cols = {
            "winning_agendas",
            "winning_tiers",
            *(f"p{p}_tier" for p in range(config.num_players)),
            *(f"p{p}_agenda" for p in range(config.num_players)),
            *(_seat_column(s) for s in SEATS),
        }
        decls = ", ".join(
            f'"{c}" {"TEXT" if c in text_cols else "INTEGER"}' for c in self.cols
        )
        self.conn.execute("DROP TABLE IF EXISTS games")
        self.conn.execute(f"CREATE TABLE games ({decls})")
        self._sql = (
            f'INSERT INTO games ({", ".join(chr(34) + c + chr(34) for c in self.cols)}) '
            f'VALUES ({", ".join("?" for _ in self.cols)})'
        )

    def write(self, data: dict[str, Any]) -> None:
        self.conn.execute(self._sql, [data[c] for c in self.cols])

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()


def open_sink(path: Path, config: Config, fmt: str):
    if fmt == "sqlite":
        return SqliteSink(path, config)
    if fmt == "csv":
        return CsvSink(path, config)
    raise ValueError(f"unknown output format: {fmt}")


def read_rows(path: Path) -> list[dict[str, Any]]:
    """Load logged games back from either format, for `analyze`."""

    if path.suffix in {".db", ".sqlite", ".sqlite3"}:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute("SELECT * FROM games")]
        conn.close()
        return rows
    with path.open(newline="", encoding="utf-8") as fh:
        out = []
        for raw in csv.DictReader(fh):
            row_: dict[str, Any] = {}
            for k, v in raw.items():
                try:
                    row_[k] = int(v)
                except (TypeError, ValueError):
                    row_[k] = v
            out.append(row_)
        return out
