"""The web rendition's index page: every card in the deck, in deck order.

One self-contained HTML file next to the images. No build step, no CDN, no
fonts to fetch -- a playtester opens it off a USB stick or a static host and it
works. Stdlib only, so it costs the test suite nothing to import.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path

#: Ink, parchment and gold, the same three the cards are printed in, defined
#: as tokens on a light ground and redefined for a dark one. The light ground
#: is a shade cooler and darker than the cards' parchment so the cards still
#: read as objects sitting on it rather than dissolving into it.
CSS = """
:root {
  --bg: #e7e3d9;
  --surface: #f3efe6;
  --text: #11243c;
  --muted: #5c6979;
  --accent: #8a6a2f;
  --rule: rgba(17, 36, 60, .16);
  --shadow: rgba(30, 26, 18, .30);
  --radius: 3.6%;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0b1725;
    --surface: #132234;
    --text: #f1e9d6;
    --muted: #9aa6bb;
    --accent: #b08a42;
    --rule: rgba(176, 138, 66, .30);
    --shadow: rgba(0, 0, 0, .55);
  }
}
:root[data-theme="dark"] {
  --bg: #0b1725;
  --surface: #132234;
  --text: #f1e9d6;
  --muted: #9aa6bb;
  --accent: #b08a42;
  --rule: rgba(176, 138, 66, .30);
  --shadow: rgba(0, 0, 0, .55);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 16px/1.55 Georgia, "Iowan Old Style", "Times New Roman", serif;
  -webkit-text-size-adjust: 100%;
}
img { max-width: 100%; }
header {
  padding: 44px 16px 28px;
  text-align: center;
  border-bottom: 1px solid var(--rule);
}
h1 {
  margin: 0 0 6px;
  font-size: clamp(28px, 5vw, 42px);
  font-weight: 700;
  letter-spacing: .01em;
  text-wrap: balance;
}
header p { margin: 0; color: var(--muted); font-size: 15px; }
nav {
  position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5;
  display: flex; flex-wrap: wrap; gap: 6px; justify-content: center;
  padding: 10px 16px;
  background: var(--bg);
  border-bottom: 1px solid var(--rule);
}
nav a {
  color: var(--muted); text-decoration: none;
  font: 600 11px/1 ui-sans-serif, system-ui, sans-serif;
  letter-spacing: .09em; text-transform: uppercase;
  padding: 7px 10px; border-radius: 999px;
}
nav a:hover { color: var(--text); background: var(--surface); }
nav a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
main { max-width: 1240px; margin: 0 auto; padding-block: 8px 64px; padding-inline: 16px; }
section { padding-top: 34px; }
h2 {
  margin: 0 0 4px; font-size: 20px; letter-spacing: .02em;
  display: flex; align-items: baseline; gap: 10px;
}
h2 .count {
  font: 400 13px/1 ui-sans-serif, system-ui, sans-serif;
  color: var(--muted); font-variant-numeric: tabular-nums;
}
section > p { margin: 0 0 18px; color: var(--muted); font-size: 14px; max-width: 62ch; }
.grid { display: grid; gap: 18px; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr)); }
figure { margin: 0; }
figure button {
  display: block; width: 100%; padding: 0; border: 0; background: none;
  cursor: zoom-in; border-radius: var(--radius);
}
figure button:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
figure img {
  display: block; width: 100%; height: auto;
  border-radius: var(--radius);
  box-shadow: 0 1px 3px var(--shadow), 0 10px 24px var(--shadow);
  transition: transform .14s ease;
}
figure button:hover img, figure button:focus-visible img { transform: translateY(-3px); }
figcaption { margin-top: 9px; font-size: 13px; line-height: 1.35; }
figcaption .slot {
  color: var(--accent); margin-right: 6px;
  font: 600 11px/1 ui-sans-serif, system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
}
figcaption .type {
  display: block; margin-top: 2px; color: var(--muted);
  font: 500 10px/1.3 ui-sans-serif, system-ui, sans-serif;
  letter-spacing: .1em; text-transform: uppercase;
}
dialog { border: 0; padding: 0; background: none; max-width: 100vw; max-height: 100vh; }
dialog::backdrop { background: rgba(6, 12, 20, .88); }
dialog img {
  max-width: min(94vw, 620px); max-height: 92vh; width: auto; height: auto;
  border-radius: 3.6%; box-shadow: 0 20px 60px rgba(0, 0, 0, .6); cursor: zoom-out;
}
footer { padding: 34px 16px 60px; text-align: center; color: var(--muted); font-size: 13px; }
footer code { font-size: 12px; color: var(--text); }
@media (prefers-reduced-motion: reduce) {
  figure img { transition: none; }
  figure button:hover img, figure button:focus-visible img { transform: none; }
}
@media (max-width: 480px) {
  .grid { grid-template-columns: repeat(auto-fill, minmax(132px, 1fr)); gap: 14px; }
}
"""

#: Opening the viewer is the only behaviour, so it is eight lines and no
#: framework. `<dialog>` brings the backdrop, Escape and focus trapping along.
JS = """
const viewer = document.getElementById('viewer');
const shown = viewer.querySelector('img');
document.querySelectorAll('figure button').forEach(button => {
  button.addEventListener('click', () => {
    const img = button.querySelector('img');
    shown.src = img.src;
    shown.alt = img.alt;
    viewer.showModal();
  });
});
viewer.addEventListener('click', () => viewer.close());
"""


@dataclass(frozen=True)
class Entry:
    """One card in the gallery."""

    slot: int
    label: str
    name: str
    type_line: str
    filename: str
    group: str


#: The blurb under each section heading, so the page explains the deck as it
#: goes rather than assuming the reader has the rules open.
GROUP_NOTES: dict[str, str] = {
    "Courtier": (
        "Forty courtiers. The four printed attributes are the whole of what an "
        "agenda reads off the board; a killed courtier can come back as a new "
        "person with these same printed values."
    ),
    "Event": (
        "Five minor and major pairs. An event hits the whole table rather than "
        "one courtier, and no Defense covers one."
    ),
    "Promotion": "Takes an occupied seat, bumping whoever is sitting in it to the outer circle.",
    "Demotion": "Empties a seat.",
    "Removal": "Takes a courtier out of play entirely.",
    "Defense": (
        "Attached to an inner-circle courtier by sacrificing a matching "
        "courtier from hand. Stops one Removal, Demotion, Strip or Mutation."
    ),
    "Strip": "Empties an attribute without spending the courtier's one mutation.",
    "Mutation": "Changes one attribute. Each attribute can be mutated once per courtier.",
    "Pivot": "Trade your agenda for one from the pool nobody was dealt.",
    "Outmaneuver": "The target loses their next turn.",
    "Agenda": (
        "Four are dealt and four stay in the fog for a Schismatic Event to "
        "draw from. These print the default thresholds; a table running a "
        "variant should play off docs/RULES.md instead."
    ),
    "Card back": "Shared by every card in the deck.",
}


def render(
    title: str,
    subtitle: str,
    entries: list[Entry],
    back: str | None,
    standalone: bool = True,
) -> str:
    """The whole page as one string of HTML.

    `standalone` writes the document wrapper, which is what a file opened off
    disk needs. Hosts that supply their own `<head>` -- a published artifact,
    for one -- take `standalone=False` and get the title, style and content
    without a second `<html>` around them.
    """

    groups: list[tuple[str, list[Entry]]] = []
    for entry in entries:
        if not groups or groups[-1][0] != entry.group:
            groups.append((entry.group, []))
        groups[-1][1].append(entry)
    if back is not None:
        groups.append(("Card back", [Entry(-1, "00", "Card back", "", back, "Card back")]))

    def slug(group: str) -> str:
        return group.lower().replace(" ", "-")

    nav = "\n".join(
        f'      <a href="#{slug(group)}">{html.escape(group)}</a>' for group, _ in groups
    )

    sections = []
    for group, group_entries in groups:
        figures = []
        for entry in group_entries:
            caption = f'<span class="slot">{html.escape(entry.label)}</span>{html.escape(entry.name)}'
            if entry.type_line:
                caption += f'<span class="type">{html.escape(entry.type_line)}</span>'
            figures.append(
                "        <figure>\n"
                "          <button type=\"button\">\n"
                f'            <img src="cards/{html.escape(entry.filename)}" '
                f'alt="{html.escape(entry.name)}" loading="lazy" decoding="async">\n'
                "          </button>\n"
                f"          <figcaption>{caption}</figcaption>\n"
                "        </figure>"
            )
        note = GROUP_NOTES.get(group, "")
        sections.append(
            f'    <section id="{slug(group)}">\n'
            f"      <h2>{html.escape(group)}"
            f'<span class="count">{len(group_entries)}</span></h2>\n'
            + (f"      <p>{html.escape(note)}</p>\n" if note else "")
            + '      <div class="grid">\n'
            + "\n".join(figures)
            + "\n      </div>\n    </section>"
        )

    body = f"""  <header>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(subtitle)}</p>
  </header>
  <nav>
{nav}
  </nav>
  <main>
{chr(10).join(sections)}
  </main>
  <footer>
    Trimmed to the printed card, bleed removed. The print rendition and the
    MPC Autofill order file are built by <code>tools/mpcfill.py</code>.
  </footer>
  <dialog id="viewer"><img alt=""></dialog>
<script>{JS}</script>
"""

    head = f"<title>{html.escape(title)}</title>\n<style>{CSS}</style>\n"
    if not standalone:
        return head + body
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        + head
        + "</head>\n<body>\n"
        + body
        + "</body>\n</html>\n"
    )


def write(
    path: Path,
    title: str,
    subtitle: str,
    entries: list[Entry],
    back: str | None,
    standalone: bool = True,
) -> Path:
    path.write_text(render(title, subtitle, entries, back, standalone), encoding="utf-8")
    return path
