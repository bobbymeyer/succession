"""The sigil printed on a courtier matches the one the browser game draws.

Two drawings of one mark: tools/sigil.py for the printed cards and
web/src/components/Sigil.tsx for the game. The game lays its live sigil where
the card prints one, so their colours and their place must agree.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from PIL import Image  # noqa: F401
except ImportError:  # pragma: no cover - print tooling is optional
    Image = None

TSX = (ROOT / "web" / "src" / "components" / "Sigil.tsx").read_text()
CSS = (ROOT / "web" / "src" / "styles.css").read_text()


def ts_colours(table: str) -> dict[str, tuple[int, int, int]]:
    body = re.search(rf"{table}: Record<string, string> = \{{(.*?)\}};", TSX, re.S).group(1)
    return {k: tuple(int(h[i : i + 2], 16) for i in (0, 2, 4)) for k, h in re.findall(r'(\w+): "#([0-9a-f]{6})"', body)}


@unittest.skipIf(Image is None, "Pillow is not installed")
class Sigil(unittest.TestCase):
    def test_the_colours_agree_with_the_game(self):
        from tools.sigil import HOUSE_COLOUR, ORIGIN_COLOUR

        self.assertEqual(ts_colours("HOUSE_COLOUR"), HOUSE_COLOUR)
        self.assertEqual(ts_colours("ORIGIN_COLOUR"), ORIGIN_COLOUR)

    def test_the_game_places_it_where_the_card_prints_it(self):
        from tools.mpcfill import TRIM_H_IN, TRIM_W_IN
        from tools.sigil import SIGIL_CENTRE_X_IN, SIGIL_CENTRE_Y_IN, SIGIL_SIZE_IN

        rule = re.search(r"\.card \.face \.sigil \{(.*?)\}", CSS, re.S).group(1)
        left = float(re.search(r"left: ([\d.]+)%", rule).group(1))
        top = float(re.search(r"top: ([\d.]+)%", rule).group(1))
        width = float(re.search(r"width: max\(\d+px, ([\d.]+)%\)", rule).group(1))
        self.assertAlmostEqual(left, 100 * SIGIL_CENTRE_X_IN / TRIM_W_IN, places=1)
        self.assertAlmostEqual(top, 100 * SIGIL_CENTRE_Y_IN / TRIM_H_IN, places=1)
        self.assertAlmostEqual(width, 100 * SIGIL_SIZE_IN / TRIM_W_IN, places=1)

    def test_every_attribute_draws_something_distinct(self):
        from tools.sigil import sigil_image

        base = ("Commons", "Godless", "None", "Imperial")
        seen = set()
        for i, values in enumerate(
            (
                ("Military", "Merchant", "Church", "Commons"),
                ("The One God", "Old Gods", "Mystery Cults", "Godless"),
                ("Argaian", "Mitreas", "Amonides", "None"),
                ("Imperial", "Barbarian"),
            )
        ):
            for value in values:
                attrs = list(base)
                attrs[i] = value
                seen.add(sigil_image(*attrs, 60).tobytes())
        # Each attribute's values look different; the base appears once per row.
        self.assertEqual(len(seen), 4 + 4 + 4 + 2 - 3)

    def test_the_sigil_clears_the_attribute_plate(self):
        from tools.mpcfill import BLEED_H_IN, CONTENT_IN, LABEL_SIZE_IN, PLATE_PAD_IN, VALUE_SIZE_IN
        from tools.sigil import SIGIL_CENTRE_Y_IN, SIGIL_SIZE_IN

        row = LABEL_SIZE_IN + VALUE_SIZE_IN + 0.086
        plate_top = BLEED_H_IN - CONTENT_IN - (2 * PLATE_PAD_IN + 2 * row - 0.034)
        bleed = (BLEED_H_IN - 3.46) / 2
        self.assertLess(bleed + SIGIL_CENTRE_Y_IN + SIGIL_SIZE_IN / 2, plate_top)


if __name__ == "__main__":
    unittest.main()
