"""The JSON boundary the browser front end talks to."""

from __future__ import annotations

import json
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from succession.analysis import summarize
from succession.logsink import read_rows
from succession.webapi import Table, options


def play_out(table: Table, updates: list, rng: random.Random) -> list:
    """Answer at random until the game ends. Returns every update seen."""

    seen = list(updates)
    while updates[-1]["result"] is None:
        prompt = updates[-1]["prompt"]
        pick = rng.choice(prompt["options"])
        choice = pick["index"] if prompt["kind"] == "turn" else pick["uid"]
        updates = json.loads(table.answer(choice))
        seen.extend(updates)
    return seen


class TableTests(unittest.TestCase):
    def test_a_whole_game(self):
        for seed in range(8):
            table = Table()
            updates = json.loads(table.new_game(json.dumps({"seed": seed})))
            seen = play_out(table, updates, random.Random(seed))

            # Only the last update of a call stops for anything.
            prompts = [u for u in seen if u["prompt"]]
            self.assertTrue(prompts)
            self.assertEqual(sum(1 for u in seen if u["result"]), 1)
            # The log arrives in pieces that add up to the whole log, once.
            log = [line for u in seen for line in u["log"]]
            self.assertEqual(log, table.session.state.log)
            # Every update is through the human's eyes.
            human = table.session.humans[0]
            self.assertTrue(all(u["seat"] == human for u in seen))

    def test_the_default_table_is_you_and_one_of_each_bot(self):
        table = Table()
        table.new_game("{}")
        self.assertEqual(sorted(table.session.tiers), ["greedy", "human", "naive", "strategic"])

    def test_bad_tables(self):
        table = Table()
        for players in (["human"], ["human", "wizard"], ["naive"] * 9):
            with self.assertRaises(ValueError):
                table.new_game(json.dumps({"players": players}))
        with self.assertRaises(ValueError):
            table.answer(0)  # nothing dealt

    def test_bots_only(self):
        table = Table()
        updates = json.loads(table.new_game(json.dumps({"players": ["naive", "greedy"], "seed": 3})))
        self.assertIsNotNone(updates[-1]["result"])
        self.assertTrue(all(u["seat"] == -1 and u["view"]["hand"] == [] for u in updates))

    def test_load_picks_up_where_it_stopped(self):
        table = Table()
        updates = json.loads(table.new_game(json.dumps({"seed": 12})))
        rng = random.Random(1)
        for _ in range(5):
            prompt = updates[-1]["prompt"]
            pick = rng.choice(prompt["options"])
            updates = json.loads(table.answer(pick["index"] if prompt["kind"] == "turn" else pick["uid"]))
            if updates[-1]["result"]:
                break
        again = Table()
        loaded = json.loads(again.load(table.record()))
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["prompt"], updates[-1]["prompt"])
        self.assertEqual(loaded[0]["view"], updates[-1]["view"])

    def test_updates_say_who_moved(self):
        table = Table()
        updates = json.loads(table.new_game(json.dumps({"seed": 5})))
        n = len(table.session.tiers)
        for u in updates:
            self.assertIn(u["actor"], range(-1, n))
        # Bot turns before the human's first move each name a bot.
        human = table.session.humans[0]
        self.assertTrue(all(u["actor"] != human for u in updates))

    def test_updates_say_what_was_played(self):
        table = Table()
        updates = json.loads(table.new_game(json.dumps({"seed": 5})))
        moved = [u for u in updates if u["action"]]
        self.assertTrue(moved)
        for u in moved:
            self.assertIn(u["action"]["kind"], {"play", "move", "discard", "pass"})
            self.assertTrue(u["action"]["text"])
        # Whatever a bot played is on the table for everyone: never a card
        # still in someone else's hand.
        me = table.session.humans[0]
        hidden = {uid for p, hand in enumerate(table.session.state.hands) if p != me for uid in hand}
        last = moved[-1]["action"]
        self.assertNotIn(last["card"], hidden)

    def test_export_is_a_log_analyze_reads(self):
        import tempfile

        records = []
        for seed, players in ((1, None), (2, ["human", "strategic"]), (3, None)):
            table = Table()
            request = {"seed": seed} if players is None else {"seed": seed, "players": players}
            play_out(table, json.loads(table.new_game(json.dumps(request))), random.Random(seed))
            records.append(table.session.record())
        unfinished = Table()
        json.loads(unfinished.new_game(json.dumps({"seed": 4})))
        records.append(unfinished.session.record())

        text = Table().export(json.dumps(records))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "games.csv"
            path.write_text(text)
            rows = read_rows(path)
        self.assertEqual(len(rows), 3)  # the unfinished game is left out
        summary = summarize(rows)
        # Four seats, two seats, four seats: the two-player game's blank
        # columns are not players.
        self.assertEqual(sum(summary["seats_by_tier"].values()), 10)
        self.assertEqual(summary["seats_by_tier"]["human"], 3)

    def test_options(self):
        data = json.loads(options())
        self.assertIn("human", data["player_types"])
        self.assertEqual(data["max_players"], 8)


if __name__ == "__main__":
    unittest.main()
