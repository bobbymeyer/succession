"""Pairing the art in `assets/` with the deck in `succession/cards.py`.

The files are named `NN_kind_slug_VVVVV_.png`, numbered in `build_cards()`
order, so slot *i* takes asset *i+1*. Position is the mapping; the kind and
slug are checked against the card so that one missing file cannot silently
shift forty portraits by one.

Stdlib only, so `tests/test_card_text.py` can check the mapping on a machine
that has never installed Pillow.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from succession.cards import CardDef  # noqa: E402

ASSET_RE = re.compile(r"^(?P<index>\d{2})_(?P<kind>[a-z]+)_(?P<slug>[a-z0-9-]+)_(?P<variant>\d+)_$")
CARDBACK_STEM = "00_cardback"


class AssetMismatch(Exception):
    """The art and the deck disagree. Carries one line per problem."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__(
            "The art in assets/ does not line up with the deck in "
            "succession/cards.py:\n  " + "\n  ".join(problems)
        )


@dataclass(frozen=True)
class Asset:
    index: int
    kind: str
    slug: str
    variant: int
    path: Path


def slugify(name: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


def scan(assets_dir: Path) -> dict[int, list[Asset]]:
    """Group the art by its leading number, each group sorted by variant."""

    by_index: dict[int, list[Asset]] = {}
    for path in sorted(assets_dir.glob("*.png")):
        if path.stem == CARDBACK_STEM:
            by_index.setdefault(0, []).append(Asset(0, "cardback", "cardback", 1, path))
            continue
        match = ASSET_RE.match(path.stem)
        if match is None:
            continue
        asset = Asset(
            index=int(match["index"]),
            kind=match["kind"],
            slug=match["slug"],
            variant=int(match["variant"]),
            path=path,
        )
        by_index.setdefault(asset.index, []).append(asset)
    for assets in by_index.values():
        assets.sort(key=lambda a: a.variant)
    return by_index


def map_to_deck(cards: tuple[CardDef, ...], by_index: dict[int, list[Asset]]) -> list[Asset]:
    """One asset per deck slot, lowest variant where the art has alternates.

    Art is numbered for the full deck as it was first drawn. A card is matched
    to its art by name, so a deck with cards left out (the major events) still
    finds each card's picture, under its original number.
    """

    by_slug: dict[str, list[Asset]] = {}
    for index, assets in by_index.items():
        if index:
            by_slug.setdefault(assets[0].slug, assets)
    chosen: list[Asset] = []
    problems: list[str] = []
    for slot, card in enumerate(cards):
        variants = by_slug.get(slugify(card.name)) or by_index.get(slot + 1)
        if not variants:
            problems.append(f"slot {slot} ({card.name}): no asset for {slugify(card.name)!r}")
            continue
        asset = variants[0]
        expected_kind = card.kind.value.lower()
        if asset.kind != expected_kind:
            problems.append(
                f"slot {slot} ({card.name}): {asset.path.name} is a "
                f"{asset.kind!r}, expected {expected_kind!r}"
            )
        elif asset.slug != slugify(card.name):
            problems.append(
                f"slot {slot}: {asset.path.name} is {asset.slug!r}, "
                f"expected {slugify(card.name)!r}"
            )
        chosen.append(asset)
    if problems:
        raise AssetMismatch(problems)
    return chosen
