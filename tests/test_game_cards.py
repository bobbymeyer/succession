"""The browser game's card images cover every name the engine can report.

The game looks a card's picture up by the name in `session.view()`, so a card
renamed in `succession/cards.py` without re-running
`python tools/mpcfill.py --profile game` would show up blank. This catches it.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from succession.agendas import AGENDAS
from succession.cards import build_cards
from succession.enums import SEATS
from succession.state import Config

CARDS = ROOT / "web" / "public" / "cards"


class GameCards(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((CARDS / "manifest.json").read_text())

    def test_every_card_agenda_and_seat_has_a_picture(self):
        # The deck the game deals: the major events are out.
        deck = build_cards(event_tiers=Config().event_tiers)
        self.assertEqual(set(self.manifest["cards"]), {c.name for c in deck})
        self.assertEqual(set(self.manifest["agendas"]), {a.name for a in AGENDAS})
        self.assertEqual(set(self.manifest["seats"]), {s.value for s in SEATS})

    def test_every_file_the_manifest_names_is_there(self):
        files = [
            *self.manifest["cards"].values(),
            *self.manifest["agendas"].values(),
            *self.manifest["seats"].values(),
            self.manifest["back"],
        ]
        for name in files:
            self.assertTrue((CARDS / name).is_file(), name)
        # ...and nothing is there that the manifest does not name.
        self.assertEqual({p.name for p in CARDS.glob("*.webp")}, set(files))


if __name__ == "__main__":
    unittest.main()
