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
from tools import assets, card_text, gallery

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


class TestGallery(unittest.TestCase):
    """The web rendition's index page. Stdlib only, so no Pillow needed."""

    def setUp(self) -> None:
        self.entries = [
            gallery.Entry(0, "01", "Beloved of the Gods", "Courtier \u00b7 Church", "01 a.jpg", "Courtier"),
            gallery.Entry(1, "41", "Quarantine", "Event \u00b7 Minor", "41 q.jpg", "Event"),
        ]

    def test_every_card_reaches_the_page(self) -> None:
        page = gallery.render("Deck", "sub", self.entries, "00 back.jpg")
        for entry in self.entries:
            self.assertIn(entry.filename, page)
            self.assertIn(entry.name, page)
        self.assertIn("00 back.jpg", page)

    def test_names_with_markup_characters_are_escaped(self) -> None:
        entry = gallery.Entry(0, "01", "Hand & <Oracle>", "Courtier", "a.jpg", "Courtier")
        page = gallery.render("Deck", "sub", [entry], None)
        self.assertNotIn("<Oracle>", page)
        self.assertIn("&amp;", page)

    def test_sections_follow_deck_order(self) -> None:
        page = gallery.render("Deck", "sub", self.entries, None)
        self.assertLess(page.index('id="courtier"'), page.index('id="event"'))

    def test_every_group_the_deck_can_produce_has_a_note(self) -> None:
        groups = {card.kind.value for card in build_cards()} | {"Agenda", "Card back"}
        self.assertEqual(groups - set(gallery.GROUP_NOTES), set())


if __name__ == "__main__":
    unittest.main()
