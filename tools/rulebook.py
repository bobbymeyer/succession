#!/usr/bin/env python3
"""The rulebook: how to play at a real table, as Markdown and as printed pages.

    python tools/rulebook.py              # rewrite docs/HOW_TO_PLAY.md

The numbers (hand size, hand limit, rounds), the seats, the agendas, the
events in the deck and what each kind of card does are read from the engine
and the printed cards, so the rulebook cannot drift from the game the bots
and the browser play. The prose around them is written here, for people with
cards in their hands; docs/RULES.md is the engine's contract, not this.

`blocks()` is the one source. `markdown()` writes it for GitHub, and
`pages()` sets it as print pages for the print-and-play PDF that
`mpcfill.py --profile sheets` builds. The only inline markup is **bold**.

`tests/test_rulebook.py` fails when docs/HOW_TO_PLAY.md is out of date.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from succession.cards import build_cards  # noqa: E402
from succession.enums import SEAT_ESTATE, CardKind  # noqa: E402
from succession.state import Config  # noqa: E402
from succession.webapi import CARD_KINDS, MAX_PLAYERS, MIN_PLAYERS  # noqa: E402
from tools import card_text  # noqa: E402

OUT = REPO_ROOT / "docs" / "HOW_TO_PLAY.md"
TITLE = "Court of Succession"


@dataclass(frozen=True)
class Block:
    """One piece of the rulebook: a heading, a paragraph, or a list.

    kind is h1, h2, p, ul, ol or dl. A paragraph or heading carries `text`;
    a list carries `items` (a dl's items are "term: text" pairs).
    """

    kind: str
    text: str = ""
    items: tuple = ()


def h1(text: str) -> Block:
    return Block("h1", text)


def h2(text: str) -> Block:
    return Block("h2", text)


def p(text: str) -> Block:
    return Block("p", " ".join(text.split()))


def ul(*items: str) -> Block:
    return Block("ul", items=tuple(" ".join(i.split()) for i in items))


def ol(*items: str) -> Block:
    return Block("ol", items=tuple(" ".join(i.split()) for i in items))


def dl(pairs) -> Block:
    return Block("dl", items=tuple((term, " ".join(text.split())) for term, text in pairs))


def blocks() -> list[Block]:
    config = Config()
    deck = build_cards(config.outmaneuver_copies, config.event_tiers)
    kinds = Counter(card.kind for card in deck)
    events = [card.name for card in deck if card.kind is CardKind.EVENT]
    agendas = card_text.AGENDA_TEXT
    hand, limit, rounds = config.starting_hand, config.hand_limit, config.max_rounds

    out = [
        h1(f"{TITLE}: how to play"),
        p(
            """The King has died, leaving his infant son to inherit the throne. You
            are one of the powerful of the empire, intriguing for the ear of the
            young monarch. Place your agents in the offices close to the king, and
            see your faction's secret agenda through before anyone sees theirs."""
        ),
        p(
            f"""For {MIN_PLAYERS} to {MAX_PLAYERS} players. This is a playtest: if a
            rule here is unclear, or a game goes strangely, we want to hear about it
            (see the end)."""
        ),
        h2("What's in the box"),
        ul(
            f"""**{len(deck)} play cards**: {kinds[CardKind.COURTIER]} courtiers and
            {len(deck) - kinds[CardKind.COURTIER]} action cards, {len(events)} of
            them events.""",
            f"**{len(agendas)} agenda cards**, one for each way to win.",
            f"""**{len(SEAT_ESTATE)} seat cards**: the inner circle, the offices
            closest to the king.""",
            "**A six-sided die**, which you supply, for the poison's saving roll.",
        ),
        h2("The aim"),
        p(
            f"""Every player holds a secret **agenda**: a shape the court could take.
            The moment the inner circle shows yours, reveal it and win -- on anyone's
            turn, the instant it is true. If one board meets two agendas at once,
            both players win."""
        ),
    ]
    if rounds:
        out.append(
            p(
                f"""If nobody has won after **{rounds} rounds** -- every player taking
                {rounds} turns -- the young king, without effective council, grows
                indulgent and tyrannical, the kingdom slips into chaos, and
                **everyone loses**. Keep a tally."""
            )
        )
    out += [
        h2("Setting up"),
        ol(
            "Lay the seven **seat cards** in a row in the middle of the table. "
            "They start empty.",
            f"""Shuffle the **agendas** and deal one to each player, face down. Look
            at yours and keep it secret. Put the rest aside face down, unseen: a
            Schismatic Event draws from them.""",
            f"""Shuffle the **play cards** and deal {hand} to each player. If you are
            dealt an event, show it, shuffle it back into the deck and take another
            card instead.""",
            "Choose a first player at random. Play goes clockwise.",
        ),
        h2("The court"),
        p(
            """The **inner circle** is the seven seats, each tied to an **estate**. A
            courtier can only sit in a seat of their own estate:"""
        ),
        ul(*(f"**{seat.value}** -- {estate.value}" for seat, estate in SEAT_ESTATE.items())),
        p(
            """The **outer circle** is every courtier in play without a seat: a
            row beside the seats, waiting. Nobody owns a courtier. Agendas read the
            board, and anyone may move any outer courtier."""
        ),
        p(
            """Every courtier card prints four things: an **estate** (Church,
            Military, Merchant, Commons), a **faith** (Old Gods, Mystery Cults, The
            One God), a **house** (Amonides, Mitreas, Argaian) or none, and an
            **origin**, Imperial or Barbarian."""
        ),
        h2("Your turn"),
        ol(
            "**Draw a card.** You may play the card you just drew.",
            """**Do one thing:** play a card from your hand; or **move** an outer
            courtier into an empty seat of their estate, which costs no card; or
            **discard & draw** -- throw a card away and draw another.""",
            f"""**Mind the hand limit.** Nothing stops you drawing, but if you hold
            more than {limit} as your turn ends, discard down to {limit} -- unless
            that turn won you the game.""",
        ),
        p(
            """A card played from your hand never goes straight into a seat: a
            courtier enters the outer circle. An **occupied** seat can only be taken
            with a promotion, which bumps the sitter back to the outer circle."""
        ),
        p(
            """When the deck runs out, shuffle the discard pile to make a new one.
            A courtier who dies goes to the discard too, and may come back later
            as somebody new."""
        ),
        h2("The cards"),
        dl(CARD_KINDS),
        p(
            """**Keeping track of changes.** A mutation or a strip changes a
            courtier for as long as they stay in play. Lay a scrap of paper or a
            coin on the card to show what changed, and take it off when they leave
            play: a courtier who returns from the discard comes back as printed. If
            a change of estate leaves a seated courtier in the wrong seat, they
            drop to the outer circle at once."""
        ),
        p(
            """**Defense, in practice.** When someone plays an attack on a seated
            courtier, pause before it resolves: going round from the attacker's
            left, anyone holding a Defense that covers it may play it. Both cards go
            to the discard and nothing happens."""
        ),
        h2("Events"),
        p(
            """Nobody holds an event. **It plays the moment it is drawn** -- at the
            top of a turn, from a discard & draw, from a Caravan -- for whoever drew
            it, and it hits the whole table. No Defense stops one. Then that player
            draws again and carries on."""
        ),
        p(
            """When an event asks every player to choose -- a courtier to name, a
            card to discard -- everyone chooses **at once**: lay a card face down,
            or point on a count of three, then reveal together."""
        ),
        dl((name, card_text.RULES[name]) for name in events),
        p(
            """A **seal** (Quarantine) lasts until just before the caster's next
            turn, so every other player takes one turn under it. Leave the card
            turned sideways on the discard pile until it lifts."""
        ),
        h2("The agendas"),
        p(
            f"""Each player is dealt one of these {len(agendas)}. Everything an agenda
            asks for must hold at once, in the inner circle unless it says
            otherwise."""
        ),
        dl((name, text) for name, _, text in agendas),
        p(
            """**A Schismatic Event** swaps your agenda: put yours face down among
            the unused ones, shuffle them, and draw one. Everyone sees you do it;
            nobody sees either card."""
        ),
        p(
            """**Revealing.** Turn your agenda face up the moment the board meets
            it. If you reveal and you were wrong, it stays face up and the game
            goes on."""
        ),
        h2("Tell us how it went"),
        p(
            """This is a playtest. After a game, the playtest form at
            github.com/bobbymeyer/succession -- *Issues*, *New issue*, *Playtest
            report* -- takes two minutes: who won, how long it took, and what
            confused you. You can also play against bots at
            bobbymeyer.github.io/succession."""
        ),
    ]
    return out


# --- Markdown -------------------------------------------------------------
def markdown(source: list[Block] | None = None) -> str:
    lines = [
        "<!-- Generated by tools/rulebook.py from the engine and the printed cards;",
        "     edit that, not this. -->",
        "",
    ]
    for block in source or blocks():
        if block.kind == "h1":
            lines += [f"# {block.text}", ""]
        elif block.kind == "h2":
            lines += [f"## {block.text}", ""]
        elif block.kind == "p":
            lines += [block.text, ""]
        elif block.kind == "ul":
            lines += [f"- {item}" for item in block.items] + [""]
        elif block.kind == "ol":
            lines += [f"{n}. {item}" for n, item in enumerate(block.items, start=1)] + [""]
        elif block.kind == "dl":
            lines += [f"- **{term}** -- {text}" for term, text in block.items] + [""]
    return "\n".join(lines).rstrip().replace(" -- ", " \u2014 ") + "\n"


# --- Print pages ----------------------------------------------------------
#: Run of text in one style: (text, bold).
Run = tuple[str, bool]


def runs(text: str) -> list[Run]:
    """Split **bold** markup into runs, and drop the *italic* stars."""

    out: list[Run] = []
    for i, part in enumerate(re.split(r"\*\*", text)):
        if part:
            out.append((part.replace("*", "").replace(" -- ", " — "), i % 2 == 1))
    return out


def pages(paper: str, dpi: int, fonts) -> list:
    """The rulebook set in two columns on A4 or Letter, at `dpi`.

    Pillow, not a layout engine: headings, paragraphs and lists, wrapped word
    by word with bold runs kept bold, and a column or a page broken between
    lines. Plenty for a rulebook a few pages long.
    """

    from PIL import Image, ImageDraw

    from tools import boardsheet

    sheet = boardsheet.Sheet(paper, dpi)
    page_w, page_h = sheet.size
    margin, gap = sheet.px(0.6), sheet.px(0.3)
    column_w = (page_w - 2 * margin - gap) // 2
    body = sheet.px(0.125)  # about 9pt
    leading = round(body * 1.32)
    fonts_by = {
        "regular": fonts.at("regular", body),
        "bold": fonts.at("bold", body),
        "h1": fonts.at("bold", sheet.px(0.26)),
        "h2": fonts.at("bold", sheet.px(0.17)),
    }
    ink, accent = (20, 20, 24), (110, 40, 30)

    result: list = []
    # `top` is where a column starts: below the title on the first page.
    state = {"page": None, "draw": None, "column": 0, "y": 0, "top": 0}

    def new_page() -> None:
        page = Image.new("RGB", sheet.size, (255, 255, 255))
        result.append(page)
        state.update(page=page, draw=ImageDraw.Draw(page), column=0, y=margin, top=margin)
        footer = fonts_by["regular"]
        label = f"{TITLE} — how to play · {len(result)}"
        state["draw"].text((margin, page_h - margin + sheet.px(0.15)), label, font=footer, fill=(120, 120, 120))

    def room(height: int) -> None:
        if state["page"] is None:
            new_page()
        if state["y"] + height > page_h - margin:
            if state["column"] == 0:
                state.update(column=1, y=state["top"])
            else:
                new_page()

    def x0() -> int:
        return margin + state["column"] * (column_w + gap)

    def wrap(parts: list[Run], width: int) -> list[list[Run]]:
        words: list[Run] = []
        for text, bold in parts:
            for word in re.split(r"(\s+)", text):
                if word and not word.isspace():
                    words.append((word, bold))
                elif word and words:
                    words[-1] = (words[-1][0] + " ", words[-1][1])
        lines: list[list[Run]] = [[]]
        used = 0
        for word, bold in words:
            font = fonts_by["bold" if bold else "regular"]
            w = font.getlength(word.rstrip())
            if lines[-1] and used + w > width:
                lines.append([])
                used = 0
            lines[-1].append((word, bold))
            used += font.getlength(word)
        return lines

    def write_lines(parts: list[Run], indent: int = 0, prefix: str = "") -> None:
        lines = wrap(parts, column_w - indent)
        for n, line in enumerate(lines):
            room(leading)
            x = x0() + indent
            if n == 0 and prefix:
                state["draw"].text((x0() + sheet.px(0.04), state["y"]), prefix, font=fonts_by["regular"], fill=ink)
            for word, bold in line:
                font = fonts_by["bold" if bold else "regular"]
                state["draw"].text((x, state["y"]), word, font=font, fill=ink)
                x += font.getlength(word)
            state["y"] += leading

    for block in blocks():
        if block.kind == "h1":
            font = fonts_by["h1"]
            room(round(font.size * 1.6))
            state["draw"].text((x0(), state["y"]), block.text, font=font, fill=accent)
            state["y"] += round(font.size * 1.6)
            state["top"] = state["y"]  # the title runs across both columns
        elif block.kind == "h2":
            font = fonts_by["h2"]
            # Keep a heading with at least three lines of what follows.
            room(round(font.size * 1.8) + 3 * leading)
            state["y"] += round(leading * 0.4)
            state["draw"].text((x0(), state["y"]), block.text, font=font, fill=accent)
            state["y"] += round(font.size * 1.45)
        elif block.kind == "p":
            write_lines(runs(block.text))
            state["y"] += round(leading * 0.45)
        elif block.kind in ("ul", "ol"):
            for n, item in enumerate(block.items, start=1):
                write_lines(runs(item), indent=sheet.px(0.2), prefix="•" if block.kind == "ul" else f"{n}.")
                state["y"] += round(leading * 0.2)
            state["y"] += round(leading * 0.3)
        elif block.kind == "dl":
            for term, text in block.items:
                write_lines([(term + ". ", True)] + runs(text))
                state["y"] += round(leading * 0.35)
            state["y"] += round(leading * 0.2)
    return result


def write_pdf(path: Path, paper: str, dpi: int, fonts) -> Path:
    rendered = pages(paper, dpi, fonts)
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered[0].save(path, "PDF", resolution=dpi, save_all=True, append_images=rendered[1:])
    return path


def main() -> int:
    OUT.write_text(markdown(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
