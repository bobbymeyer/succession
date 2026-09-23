"""Play a seat at the table from a terminal: `python -m succession play`.

A thin front end over `GameSession`. Everything it prints comes from
`session.view()` and `session.prompt_json()`, the same picture the browser
front end will get, so it shows nothing a player at the table could not see.
"""

from __future__ import annotations

from typing import Callable, Optional

from .session import COURTIER, OVER, TURN, GameSession

RULE = "-" * 72


def _courtier(card: dict) -> str:
    """Name plus live attributes; a changed attribute is starred."""

    bits = []
    for attribute in ("estate", "faith", "family", "origin"):
        mark = "*" if attribute in card["changed"] else ""
        bits.append(f"{card[attribute]}{mark}")
    text = f"{card['name']} [{' / '.join(bits)}]"
    if card["defense"]:
        text += f" +{card['defense']['name']}"
    return text


def _card(card: dict) -> str:
    if card["kind"] == "Courtier":
        return _courtier(card)
    estate = f", {card['estate']}" if card["estate"] else ""
    return f"{card['name']} ({card['kind']}{estate})"


def _who(player: dict, you: int) -> str:
    return f"P{player['seat']} {'you' if player['seat'] == you else player['tier']}"


def format_view(view: dict) -> str:
    you = view["you"]
    lines = [RULE, f"Turn {view['turn']}"]

    table = []
    for p in view["players"]:
        bits = [_who(p, you), f"{p['hand']} cards"]
        if p["agenda"]:
            bits.append(p["agenda"]["name"])
        if p["skips_next_turn"]:
            bits.append("skips next turn")
        table.append(", ".join(bits))
    lines.append("Table: " + " | ".join(table))

    lines.append("Inner circle:")
    for seat in view["seats"]:
        occupant = _courtier(seat["courtier"]) if seat["courtier"] else "--"
        lines.append(f"  {seat['seat']:<24} {occupant}")
    outer = [_courtier(c) for c in view["outer"]]
    lines.append(f"Outer circle ({len(outer)}):")
    lines.extend(f"  {c}" for c in outer)

    top = f" (top: {view['discard_top']['name']})" if view["discard_top"] else ""
    pile = f"Deck {view['deck']}, discard {view['discard']}{top}"
    if view["frozen"]["board"]:
        pile += " -- SIEGE: the whole board is sealed"
    elif view["frozen"]["inner"]:
        pile += " -- QUARANTINE: the inner circle is sealed"
    lines.append(pile)

    if you >= 0:
        agenda = view["players"][you]["agenda"]
        lines.append(f"Your agenda: {agenda['name']}")
        lines.append("Your hand:")
        lines.extend(f"  {_card(c)}" for c in view["hand"])
    return "\n".join(lines)


def format_prompt(prompt: dict) -> str:
    if prompt["kind"] == TURN:
        head = "Your move:"
        options = [o["text"] for o in prompt["options"]]
    elif prompt["kind"] == COURTIER:
        head = f"{prompt['card']['name']}: name a courtier to die:"
        options = [_courtier(c) for c in prompt["options"]]
    else:
        head = f"{prompt['card']['name']}: choose a card to discard:"
        options = [_card(c) for c in prompt["options"]]
    lines = [head]
    lines.extend(f"  {i:>2}. {text}" for i, text in enumerate(options, start=1))
    return "\n".join(lines)


def format_result(session: GameSession) -> str:
    view = session.view(-1)
    lines = [RULE, session.state.describe(), ""]
    for p in view["players"]:
        mark = "  <- WINNER" if p["seat"] in view["winners"] else ""
        you = " (you)" if p["seat"] in session.humans else ""
        lines.append(f"P{p['seat']} {p['tier']}{you}: {p['agenda']['name']}{mark}")
    if session.timeout:
        lines.append(f"Chaos grips the empire. No one wins after {session.state.turn} turns.")
    else:
        lines.append(f"Game over after {session.state.turn} turns.")
    return "\n".join(lines)


def play(
    session: GameSession,
    read: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
) -> bool:
    """Drive `session` until it ends or the player quits. True if it ended."""

    shown = 0  # log lines already printed

    def catch_up() -> None:
        nonlocal shown
        log = session.state.log
        for line in log[shown:]:
            write(line)
        shown = len(log)

    if session.humans:
        write(f"You are {', '.join(f'P{h}' for h in session.humans)}. Type a number, or q to quit.")
    prompt = session.advance()
    while prompt.kind != OVER:
        catch_up()
        write(format_view(session.view(prompt.player)))
        data = session.prompt_json(prompt)
        write(format_prompt(data))
        choice = _ask(read, write, len(data["options"]))
        if choice is None:
            return False
        if prompt.kind == TURN:
            prompt = session.answer(choice)
        else:
            prompt = session.answer(data["options"][choice]["uid"])
    catch_up()
    write(format_result(session))
    return True


def _ask(read: Callable[[str], str], write: Callable[[str], None], count: int) -> Optional[int]:
    while True:
        try:
            raw = read("> ").strip().lower()
        except EOFError:
            return None
        if raw in {"q", "quit", "exit"}:
            return None
        if raw.isdigit() and 1 <= int(raw) <= count:
            return int(raw) - 1
        write(f"Type a number from 1 to {count}, or q to quit.")
