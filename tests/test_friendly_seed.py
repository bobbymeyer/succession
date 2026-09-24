"""The first game's seed stays kind as the engine changes around it."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from friendly_seed import FAITH_ASCENDANT, HOUSE_RISING, TABLE, opening, stand_in_games  # noqa: E402


def first_game_seed() -> int:
    source = (ROOT / "web" / "src" / "firstGame.ts").read_text()
    return int(re.search(r"FIRST_GAME_SEED = (\d+);", source).group(1))


class FriendlySeed(unittest.TestCase):
    def test_the_page_deals_the_table_the_seed_was_chosen_for(self):
        source = (ROOT / "web" / "src" / "firstGame.ts").read_text()
        bots = re.search(r"FIRST_GAME_TABLE = \[(.*?)\]", source).group(1)
        self.assertEqual(tuple(re.findall(r'"(\w+)"', bots)), TABLE[1:])

    def test_the_first_deal_is_a_kind_one(self):
        seed = first_game_seed()
        o = opening(seed)
        self.assertEqual(o["position"], 0, "you move first")
        self.assertIn(o["agenda"].kind, (FAITH_ASCENDANT, HOUSE_RISING))
        self.assertGreaterEqual(o["helpful"], 2)
        games = stand_in_games(seed, o["seat"])
        self.assertTrue(all(won for _, won, _ in games), games)


if __name__ == "__main__":
    unittest.main()
