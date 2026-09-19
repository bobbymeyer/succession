"""Summary statistics over a batch of logged games."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from typing import Any, Sequence

from .agendas import AGENDAS_BY_KEY
from .enums import SEATS

TIER_ORDER = ("naive", "greedy", "strategic")


def _tiers(row: dict[str, Any]) -> list[str]:
    out = []
    i = 0
    while f"p{i}_tier" in row:
        out.append(row[f"p{i}_tier"])
        i += 1
    return out


def summarize(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"games": 0}

    turns = [int(r["turns"]) for r in rows]
    decided = [r for r in rows if not int(r["timeout"])]

    seats_by_tier: Counter[str] = Counter()
    wins_by_tier: Counter[str] = Counter()
    dealt_by_agenda: Counter[str] = Counter()
    wins_by_agenda: Counter[str] = Counter()
    dealt_by_tier_agenda: dict[tuple[str, str], int] = defaultdict(int)
    wins_by_tier_agenda: dict[tuple[str, str], int] = defaultdict(int)

    for r in rows:
        for p, tier in enumerate(_tiers(r)):
            agenda = r[f"p{p}_agenda"]
            won = int(r[f"p{p}_won"])
            seats_by_tier[tier] += 1
            dealt_by_agenda[agenda] += 1
            dealt_by_tier_agenda[(tier, agenda)] += 1
            if won:
                wins_by_tier[tier] += 1
                wins_by_agenda[agenda] += 1
                wins_by_tier_agenda[(tier, agenda)] += 1

    with_strategic = [r for r in rows if "strategic" in _tiers(r)]
    without_strategic = [r for r in rows if "strategic" not in _tiers(r)]

    def _non_strategic_win_rate(subset: Sequence[dict[str, Any]]) -> float | None:
        seats = wins = 0
        for r in subset:
            for p, tier in enumerate(_tiers(r)):
                if tier == "strategic":
                    continue
                seats += 1
                wins += int(r[f"p{p}_won"])
        return wins / seats if seats else None

    inner_filled = [int(r["inner_filled"]) for r in rows]

    return {
        "games": len(rows),
        "decided": len(decided),
        "timeouts": len(rows) - len(decided),
        "timeout_rate": (len(rows) - len(decided)) / len(rows),
        "turns_mean": statistics.fmean(turns),
        "turns_median": statistics.median(turns),
        "turns_min": min(turns),
        "turns_max": max(turns),
        "rounds_mean": statistics.fmean(int(r["rounds"]) for r in rows),
        "double_wins": sum(int(r["double_win"]) for r in rows),
        "double_win_rate": sum(int(r["double_win"]) for r in rows) / len(rows),
        "seats_by_tier": dict(seats_by_tier),
        "wins_by_tier": dict(wins_by_tier),
        "win_rate_by_tier": {
            t: wins_by_tier[t] / seats_by_tier[t] for t in seats_by_tier
        },
        "dealt_by_agenda": dict(dealt_by_agenda),
        "wins_by_agenda": dict(wins_by_agenda),
        "win_rate_by_agenda": {
            a: wins_by_agenda[a] / dealt_by_agenda[a] for a in dealt_by_agenda
        },
        "win_rate_by_tier_agenda": {
            f"{t}|{a}": wins_by_tier_agenda[(t, a)] / n
            for (t, a), n in dealt_by_tier_agenda.items()
        },
        "suppression": {
            "games_with_strategic": len(with_strategic),
            "games_without_strategic": len(without_strategic),
            "non_strategic_win_rate_with": _non_strategic_win_rate(with_strategic),
            "non_strategic_win_rate_without": _non_strategic_win_rate(without_strategic),
        },
        "reshuffles_mean": statistics.fmean(int(r["reshuffles"]) for r in rows),
        "inner_filled_mean": statistics.fmean(inner_filled),
        "courtiers_killed_mean": statistics.fmean(int(r["courtiers_killed"]) for r in rows),
    }


def format_summary(s: dict[str, Any]) -> str:
    if not s.get("games"):
        return "no games logged"

    lines = [
        "=" * 64,
        f"Games: {s['games']}   decided: {s['decided']}   "
        f"timeouts: {s['timeouts']} ({s['timeout_rate']:.1%})",
        f"Game length (player-turns): mean {s['turns_mean']:.1f}  "
        f"median {s['turns_median']:.0f}  min {s['turns_min']}  max {s['turns_max']}  "
        f"(mean {s['rounds_mean']:.1f} rounds)",
        f"Double wins: {s['double_wins']} ({s['double_win_rate']:.2%})",
        f"Mean inner seats filled at end: {s['inner_filled_mean']:.2f}/{len(SEATS)}   "
        f"courtiers killed: {s['courtiers_killed_mean']:.1f}   "
        f"deck reshuffles: {s['reshuffles_mean']:.2f}",
        "-" * 64,
        "Win rate by bot tier (per seat played):",
    ]
    order = [t for t in TIER_ORDER if t in s["seats_by_tier"]]
    order += [t for t in sorted(s["seats_by_tier"]) if t not in TIER_ORDER]
    for tier in order:
        lines.append(
            f"  {tier:<10} {s['wins_by_tier'].get(tier, 0):>6} wins / "
            f"{s['seats_by_tier'][tier]:>6} seats = {s['win_rate_by_tier'][tier]:6.2%}"
        )

    lines += ["-" * 64, "Win rate by agenda (per time dealt):"]
    for key in sorted(s["dealt_by_agenda"], key=lambda k: -s["win_rate_by_agenda"][k]):
        name = AGENDAS_BY_KEY[key].name if key in AGENDAS_BY_KEY else key
        lines.append(
            f"  {name:<32} {s['wins_by_agenda'].get(key, 0):>6} / "
            f"{s['dealt_by_agenda'][key]:>6} = {s['win_rate_by_agenda'][key]:6.2%}"
        )

    sup = s["suppression"]
    lines += ["-" * 64, "Strategic-bot suppression:"]
    if sup["non_strategic_win_rate_with"] is None or sup["non_strategic_win_rate_without"] is None:
        have = "with" if sup["games_with_strategic"] else "without"
        lines.append(
            f"  all {s['games']} games were played {have} a strategic bot; "
            "run a second batch with the other mix to compare"
        )
    else:
        lines.append(
            f"  non-strategic win rate with a strategic bot at the table: "
            f"{sup['non_strategic_win_rate_with']:.2%}"
        )
        lines.append(
            f"  non-strategic win rate without one:                        "
            f"{sup['non_strategic_win_rate_without']:.2%}"
        )
    lines.append("=" * 64)
    return "\n".join(lines)
