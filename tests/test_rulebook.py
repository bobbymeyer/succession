"""The printed rulebook, and the print-and-play card sheets.

docs/HOW_TO_PLAY.md is generated from the engine by tools/rulebook.py; it must
be regenerated whenever a rule it reads changes. The page layouts need Pillow
and skip without it, as the board sheet's tests do.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from succession.cards import build_cards
from succession.enums import SEAT_ESTATE, CardKind
from succession.state import Config
from succession.webapi import CARD_KINDS
from tools import card_text, rulebook

try:
    from PIL import Image

    from tools import cardsheet
    from tools.boardsheet import Sheet
    from tools.mpcfill import Fonts
except ImportError:  # pragma: no cover - exercised only without Pillow
    cardsheet = None

#: A trimmed card at 300 DPI: 2.48 x 3.46 in.
CARD = (744, 1038)


class HowToPlay(unittest.TestCase):
    def test_the_committed_rulebook_is_current(self):
        self.assertEqual(
            rulebook.OUT.read_text(encoding="utf-8"),
            rulebook.markdown(),
            "docs/HOW_TO_PLAY.md is stale: run python tools/rulebook.py",
        )

    def test_it_names_every_seat_card_kind_event_and_agenda(self):
        text = rulebook.markdown()
        config = Config()
        events = [c.name for c in build_cards(config.outmaneuver_copies, config.event_tiers) if c.kind is CardKind.EVENT]
        names = [seat.value for seat in SEAT_ESTATE] + [name for name, _ in CARD_KINDS] + events
        names += [name for name, _, _ in card_text.AGENDA_TEXT]
        for name in names:
            self.assertIn(f"**{name}**", text)

    def test_it_says_the_numbers_the_engine_plays_by(self):
        text = rulebook.markdown()
        config = Config()
        self.assertIn(f"deal {config.starting_hand} to each player", text)
        self.assertIn(f"more than {config.hand_limit} as your turn ends", text)
        self.assertIn(f"after **{config.max_rounds} rounds**", text)


@unittest.skipIf(cardsheet is None, "Pillow is not installed")
class PrintAndPlay(unittest.TestCase):
    def test_nine_cards_fit_at_true_size_on_both_papers(self):
        for paper in ("a4", "letter"):
            sheet = Sheet(paper, 300)
            left, top = cardsheet.origin(sheet, CARD)
            # A home printer reaches to about a quarter inch of the edge.
            self.assertGreaterEqual(left, sheet.px(0.25), paper)
            self.assertGreaterEqual(top, sheet.px(0.25), paper)

    def test_every_card_gets_a_place_and_the_backs_a_page(self):
        cards = cardsheet.Cards()
        for shade in range(10):
            cards.add(Image.new("RGB", CARD, (shade * 20, 0, 0)))
        back = Image.new("RGB", CARD, (0, 0, 200))
        pages = cardsheet.pages(cards, back, "letter", 300, Fonts())
        self.assertEqual(len(pages), 3)  # nine, one, and the backs
        sheet = Sheet("letter", 300)
        left, top = cardsheet.origin(sheet, CARD)
        # Held as JPEG, so a colour comes back within a few levels.
        def near(page, xy, colour):
            got = page.getpixel(xy)
            self.assertTrue(all(abs(a - b) <= 6 for a, b in zip(got, colour)), f"{got} is not {colour}")

        near(pages[1], (left + 10, top + 10), (180, 0, 0))  # the tenth card
        near(pages[1], (left + CARD[0] + 10, top + 10), (255, 255, 255))  # and nothing beside it
        near(pages[2], (left + CARD[0] * 2 + 10, top + CARD[1] * 2 + 10), (0, 0, 200))

    def test_the_rulebook_sets_as_pages(self):
        for paper in ("a4", "letter"):
            pages = rulebook.pages(paper, 100, Fonts())
            self.assertGreaterEqual(len(pages), 1)
            self.assertEqual(pages[0].size, Sheet(paper, 100).size)


if __name__ == "__main__":
    unittest.main()
