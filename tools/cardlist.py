"""`docs/CARDS.md`: every card in the deck as a picture and a line of text.

The gallery in `tools/gallery.py` is the same deck for a browser; this is the
same deck for anyone reading the repository, which means GitHub-flavoured
Markdown and images small enough to commit. Stdlib only.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

#: How wide each thumbnail renders in the table. The files are twice this, so
#: they stay sharp on a high-density screen.
THUMB_WIDTH = 132


@dataclass(frozen=True)
class Row:
    """One card: what it is called, what it is, and what it does."""

    label: str
    name: str
    type_line: str
    detail: str
    image: str
    group: str


def slugify(name: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


#: The column heading for the last column, per group. Courtiers list printed
#: attributes; everything else prints rules text.
DETAIL_HEADING: dict[str, str] = {"Courtier": "Printed attributes"}

#: What each group is, in one line, above its table.
GROUP_NOTES: dict[str, str] = {
    "Courtier": (
        "Forty courtiers. These four printed attributes are the whole of what "
        "an agenda reads off the board. A courtier who dies goes to the "
        "discard and may come back as a new person carrying exactly these "
        "values again -- never the mutations the dead one had collected."
    ),
    "Event": (
        "Ten events in five minor/major pairs. An event hits the whole table "
        "rather than one courtier, and no Defense covers one."
    ),
    "Promotion": (
        "Takes an *occupied* seat of the named estate, bumping the sitting "
        "courtier out to the outer circle. The wildcard `Promotion` works on "
        "any estate."
    ),
    "Demotion": "Sends an inner-circle courtier out and leaves the seat empty.",
    "Removal": (
        "Takes a courtier out of play. They go to the discard, so the epithet "
        "may return later on somebody new."
    ),
    "Defense": (
        "Attached to an inner-circle courtier ahead of time, paid for by "
        "sacrificing a courtier of the named estate from your hand. The estate "
        "constrains the *sacrifice*, not the courtier being guarded."
    ),
    "Strip": (
        "Empties an attribute. A strip does not spend the courtier's one "
        "mutation, so the slot can be filled again later."
    ),
    "Mutation": (
        "Changes one attribute. Each attribute may be mutated at most once per "
        "courtier."
    ),
    "Pivot": "Trades your agenda for one out of the pool nobody was dealt.",
    "Outmaneuver": "The targeted player loses their next turn, draw included.",
    "Agenda": (
        "Four are dealt face down and four stay in the fog for a Schismatic "
        "Event to draw from. The thresholds printed here are the defaults in "
        "`succession/agendas.py`; a table running a variant should play off "
        "`docs/RULES.md` instead."
    ),
    "Seat": (
        "The board: seven chairs, laid out on the table for courtiers to be "
        "moved into. Each is bordered in its estate's colour, so a courtier "
        "matches its chair by edge alone. Church, Military and Merchant each "
        "seat an interchangeable pair; Commons seats one."
    ),
    "Card back": "Shared by every card in the deck.",
}


def escape(text: str) -> str:
    """Markdown table cells cannot carry a raw pipe or a line break."""

    return text.replace("|", "\\|").replace("\n", " ")


def render(rows: list[Row], back: Row | None, zip_link: str | None = None) -> str:
    """The whole of `docs/CARDS.md`."""

    groups: list[tuple[str, list[Row]]] = []
    for row in rows:
        if not groups or groups[-1][0] != row.group:
            groups.append((row.group, []))
        groups[-1][1].append(row)
    if back is not None:
        groups.append(("Card back", [back]))

    total = len(rows)
    out: list[str] = [
        "# The deck",
        "",
        f"All {total} cards, in the order `succession/cards.py` builds them: the "
        "84-card play deck followed by the eight agendas. Every card here is "
        "the real print file, trimmed the way the cutter leaves it.",
        "",
    ]
    if zip_link:
        out += [
            f"**[Download the print-ready deck]({zip_link})** -- the card images "
            "plus the MPC Autofill order file, ready to order. "
            "[docs/PRINTING.md](PRINTING.md) has the steps.",
            "",
        ]
    out += [
        "Rebuild any of this with `python tools/mpcfill.py` -- see "
        "[docs/PRINTING.md](PRINTING.md).",
        "",
        "## Contents",
        "",
    ]
    for group, group_rows in groups:
        anchor = slugify(group)
        out.append(f"- [{group}](#{anchor}) ({len(group_rows)})")
    out.append("")

    for group, group_rows in groups:
        heading = DETAIL_HEADING.get(group, "What it does")
        out += [f"## {group}", ""]
        note = GROUP_NOTES.get(group)
        if note:
            out += [note, ""]
        out += [
            f"| | Card | Type | {heading} |",
            "|---|---|---|---|",
        ]
        for row in group_rows:
            thumb = (
                f'<img src="{row.image}" alt="{escape(row.name)}" width="{THUMB_WIDTH}">'
            )
            out.append(
                f"| {thumb} | **{escape(row.name)}**<br><sub>{escape(row.label)}</sub> "
                f"| {escape(row.type_line)} | {escape(row.detail)} |"
            )
        out.append("")

    out += [
        "---",
        "",
        "Generated by `python tools/mpcfill.py --profile docs`. Editing this "
        "file by hand will not survive the next build -- change "
        "`tools/card_text.py` or `tools/cardlist.py` instead.",
        "",
    ]
    return "\n".join(out)


def write(path: Path, rows: list[Row], back: Row | None, zip_link: str | None = None) -> Path:
    path.write_text(render(rows, back, zip_link), encoding="utf-8")
    return path
