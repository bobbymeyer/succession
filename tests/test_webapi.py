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

    def test_a_new_game_starts_with_the_table_as_dealt(self):
        # Before anyone moves, so the page can show you your agenda and wait.
        for seed in range(6):
            table = Table()
            first = json.loads(table.new_game(json.dumps({"seed": seed})))[0]
            human = table.session.humans[0]
            self.assertEqual(first["view"]["turn"], 0)
            self.assertEqual((first["actor"], first["action"], first["prompt"]), (-1, None, None))
            self.assertEqual(first["view"]["players"][human]["agenda"]["key"], table.session.state.agendas[human])
            self.assertTrue(first["view"]["hand"])

    def test_events_say_what_they_did(self):
        from succession.cards import EVENT_CARDS

        seen = {}
        for seed in range(60):
            table = Table()
            updates = json.loads(table.new_game(json.dumps({"seed": seed})))
            for u in play_out(table, updates, random.Random(seed)):
                for event in u["events"]:
                    # Every event now plays the moment it is drawn.
                    self.assertTrue(event["drawn"])
                    self.assertIn(event["player"], range(len(table.session.tiers)))
                    self.assertTrue(event["summary"])
                    self.assertTrue(event["effects"])
                    for effect in event["effects"]:
                        self.assertIn(effect["tone"], {"loss", "gain", "neutral"})
                    # Nobody dies and lives in the same report.
                    self.assertFalse({c["uid"] for c in event["fallen"]} & {c["uid"] for c in event["spared"]})
                    seen[event["card"]["name"]] = event
        # The five minor events; the majors are out of the deck.
        self.assertEqual(set(seen), {c.name for c in EVENT_CARDS if c.tier == "minor"})
        self.assertTrue(seen["Debasement of the Coinage"]["discarded"])
        self.assertTrue(seen["Poisoning at the Feast"]["effects"])

    def test_an_event_is_reported_once(self):
        # A turn that opens with an event sends it once, not again with the
        # question that follows.
        for seed in range(40):
            table = Table()
            updates = json.loads(table.new_game(json.dumps({"seed": seed})))
            seen = play_out(table, updates, random.Random(seed))
            for before, after in zip(seen, seen[1:]):
                if before["events"]:
                    self.assertNotEqual(before["events"], after["events"], seed)

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
        # Bot moves before the human's first move each name a bot; the human
        # is named only as their own turn opens, with nothing played yet.
        human = table.session.humans[0]
        self.assertTrue(all(u["actor"] != human or not u["action"] for u in updates))

    def test_updates_say_what_was_played(self):
        # A deal where bots move before the human does.
        for seed in range(5, 50):
            table = Table()
            updates = json.loads(table.new_game(json.dumps({"seed": seed})))
            moved = [u for u in updates if u["action"]]
            if moved:
                break
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

    def test_options_carry_the_rules_the_game_plays(self):
        # The page's rules come from the engine, so they follow any change.
        from succession.cards import EVENT_CARDS
        from succession.state import Config

        rules = json.loads(options())["rules"]
        config = Config()
        self.assertEqual(rules["hand_limit"], config.hand_limit)
        self.assertEqual(len(rules["agendas"]), 8)
        conquest = next(a for a in rules["agendas"] if a["name"] == "Barbarian Conquest")
        self.assertEqual(conquest["clauses"], ["3 barbarians seated", "1 more waiting in the outer circle"])
        self.assertEqual(
            [e["name"] for e in rules["events"]],
            [c.name for c in EVENT_CARDS if c.tier in config.event_tiers],
        )
        self.assertTrue(all(e["summary"] for e in rules["events"]))


if __name__ == "__main__":
    unittest.main()
