"""The printed deck must agree with the simulated one.

These are the checks that catch drift: a card added to `build_cards()` with no
rules text written for it, or art whose numbering has slipped against the deck
order. Stdlib only -- `tools/mpcfill.py` needs Pillow to draw, but nothing
here does.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from succession.cards import build_cards
from succession.courtiers import COURTIERS_BY_NAME
from succession.enums import CardKind
from tools import assets, card_text

ASSETS_DIR = REPO_ROOT / "assets"


class TestPrintedText(unittest.TestCase):
    def setUp(self) -> None:
        self.cards = build_cards()

    def test_every_action_card_has_rules_text(self) -> None:
        for card in self.cards:
            if card.is_courtier:
                continue
            with self.subTest(card=card.name):
                self.assertTrue(card_text.rules_for(card).strip())

    def test_no_orphaned_rules_text(self) -> None:
        """Text for a card that is no longer in the deck is text nobody reads."""

        printed = {card.name for card in self.cards if not card.is_courtier}
        self.assertEqual(set(card_text.RULES) - printed, set())

    def test_every_courtier_is_in_the_attribute_table(self) -> None:
        for card in self.cards:
            if card.is_courtier:
                self.assertIn(card.name, COURTIERS_BY_NAME)

    def test_type_line_names_the_kind(self) -> None:
        for card in self.cards:
            with self.subTest(card=card.name):
                line = card_text.type_line(card)
                self.assertTrue(line.startswith(card.kind.value))

    def test_estate_cards_print_their_estate(self) -> None:
        estate_kinds = {
            CardKind.PROMOTION,
            CardKind.DEMOTION,
            CardKind.REMOVAL,
            CardKind.DEFENSE,
            CardKind.COURTIER,
        }
        for card in self.cards:
            if card.kind not in estate_kinds:
                continue
            with self.subTest(card=card.name):
                expected = card.estate.value if card.estate else card_text.ANY_ESTATE
                self.assertIn(expected, card_text.type_line(card))

    def test_one_agenda_card_per_agenda(self) -> None:
        from succession.agendas import AGENDAS

        self.assertEqual(
            [name for name, _, _ in card_text.AGENDA_TEXT],
            [agenda.name for agenda in AGENDAS],
        )


class TestArtMapping(unittest.TestCase):
    """The art is numbered in deck order; this is what pins it there."""

    def setUp(self) -> None:
        if not ASSETS_DIR.is_dir():
            self.skipTest("no assets/ directory in this checkout")
        self.cards = build_cards()
        self.by_index = assets.scan(ASSETS_DIR)

    def test_every_deck_slot_has_art_matching_its_card(self) -> None:
        chosen = assets.map_to_deck(self.cards, self.by_index)
        self.assertEqual(len(chosen), len(self.cards))

    def test_card_back_exists(self) -> None:
        self.assertIn(0, self.by_index)

    def test_slugify_round_trips_the_awkward_names(self) -> None:
        for name, expected in (
            ("The Dog of the Agora", "the-dog-of-the-agora"),
            ("Coin-Counter of the Assembly", "coin-counter-of-the-assembly"),
            ("Priest of the Two-Horned God", "priest-of-the-two-horned-god"),
            ("Debasement of the Coinage", "debasement-of-the-coinage"),
        ):
            self.assertEqual(assets.slugify(name), expected)

    def test_a_shifted_asset_is_caught(self) -> None:
        """Drop slot 0's art and the mapping must complain, not quietly shift."""

        shifted = {i: a for i, a in self.by_index.items() if i != 1}
        with self.assertRaises(assets.AssetMismatch):
            assets.map_to_deck(self.cards, shifted)


if __name__ == "__main__":
    unittest.main()
