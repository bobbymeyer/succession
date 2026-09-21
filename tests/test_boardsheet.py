"""The print-at-home board sheet.

Separate from `test_card_text.py` because laying out a page needs Pillow, and
that file is deliberately stdlib-only. Skips rather than fails where Pillow is
not installed, since the simulator does not need it.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from PIL import Image

    from tools import boardsheet
except ImportError:  # pragma: no cover - exercised only without Pillow
    boardsheet = None

from succession.enums import SEAT_ESTATE

#: A trimmed card at 300 DPI: 2.48 x 3.46 in.
CARD = (744, 1038)


@unittest.skipIf(boardsheet is None, "Pillow is not installed")
class TestBoardSheet(unittest.TestCase):
    def cards(self, count: int = len(SEAT_ESTATE)) -> list:
        return [Image.new("RGB", CARD, (210, 210, 210)) for _ in range(count)]

    def test_page_is_the_paper_size_at_the_given_dpi(self) -> None:
        for paper, (width, height) in boardsheet.PAPERS.items():
            with self.subTest(paper=paper):
                sheet = boardsheet.Sheet(paper, 300)
                self.assertEqual(sheet.size, (round(width * 300), round(height * 300)))

    def test_cards_are_never_scaled_to_fit(self) -> None:
        """A seat card sits beside the courtiers it receives, so it prints at size."""

        for paper in boardsheet.PAPERS:
            with self.subTest(paper=paper):
                sheet = boardsheet.Sheet(paper, 300)
                across, down = boardsheet.grid(sheet, CARD)
                gutter = sheet.px(boardsheet.GUTTER_IN)
                margins = 2 * sheet.px(boardsheet.MARGIN_IN)
                self.assertLessEqual(across * CARD[0] + (across - 1) * gutter + margins, sheet.size[0])
                self.assertLessEqual(down * CARD[1] + (down - 1) * gutter + margins, sheet.size[1])

    def test_the_seven_seats_paginate_evenly(self) -> None:
        """Seven over two pages is four and three, not six and a lonely one."""

        from tools.mpcfill import Fonts

        fonts = Fonts()
        for paper in boardsheet.PAPERS:
            with self.subTest(paper=paper):
                pages = boardsheet.build_pages(self.cards(), boardsheet.Sheet(paper, 300), fonts, "t")
                self.assertEqual(len(pages), 2)

    def test_an_oversized_card_still_yields_a_page(self) -> None:
        """Better a visibly wrong page than a divide by zero."""

        sheet = boardsheet.Sheet("a4", 300)
        self.assertEqual(boardsheet.grid(sheet, (9999, 9999)), (1, 1))

    def test_no_cards_means_no_pages(self) -> None:
        from tools.mpcfill import Fonts

        self.assertEqual(boardsheet.build_pages([], boardsheet.Sheet("a4", 300), Fonts(), "t"), [])


if __name__ == "__main__":
    unittest.main()
