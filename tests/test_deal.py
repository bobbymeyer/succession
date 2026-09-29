"""Stacked deals: a game set up as a test (or the first game) needs it."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from succession import deal  # noqa: E402
from succession.agendas import AGENDAS_BY_KEY, HOUSE_RISING  # noqa: E402
from succession.enums import Seat  # noqa: E402
from succession.session import HUMAN, TURN, GameSession  # noqa: E402
from succession.state import Config  # noqa: E402

TABLE = (HUMAN, "naive", "greedy", "strategic")


def names(state, uids):
    return [state.name(u) for u in uids]


class Deals(unittest.TestCase):
    def test_a_deal_sets_what_it_names_and_shuffles_the_rest(self):
        spec = {
            "first": 2,
            "agendas": {"0": "balance", "3": "faith_old_gods"},
            "hands": {"0": ["Golden Thumb", "Promotion"]},
            "deck": ["Caravan", "Silver Tongue"],
            "seats": {"Oracle": "Hand of the Oracle"},
            "outer": ["Master Mason"],
        }
        for seed in (1, 2):
            state = GameSession(Config(players=TABLE), seed, deal=spec).state
            self.assertEqual(state.current, 2)
            self.assertEqual((state.agendas[0], state.agendas[3]), ("balance", "faith_old_gods"))
            self.assertEqual(len(set(state.agendas)), 4)
            self.assertEqual(names(state, state.hands[0]), ["Golden Thumb", "Promotion"])
            self.assertTrue(all(len(h) == 5 for h in state.hands[1:]))
            self.assertEqual(state.name(state.seats[Seat.ORACLE]), "Hand of the Oracle")
            self.assertEqual(names(state, state.outer), ["Master Mason"])
            # The deck is drawn from its end: Caravan comes first.
            self.assertEqual(names(state, state.deck[-2:]), ["Silver Tongue", "Caravan"])
            everywhere = state.deck + [u for h in state.hands for u in h] + state.outer + [state.seats[Seat.ORACLE]]
            self.assertEqual(sorted(everywhere), list(range(len(state.cards))))

    def test_seats_are_never_shuffled_under_a_deal(self):
        session = GameSession(Config(players=TABLE), 9, deal={})
        self.assertEqual(session.tiers, list(TABLE))
        self.assertEqual(session.humans, [0])

    def test_a_deal_that_cannot_be_dealt_says_why(self):
        with self.assertRaisesRegex(ValueError, "no copy of it is left"):
            GameSession(Config(players=TABLE), 1, deal={"hands": {"0": ["Silver Tongue"]}, "deck": ["Silver Tongue"]})
        with self.assertRaisesRegex(ValueError, "unknown agenda"):
            GameSession(Config(players=TABLE), 1, deal={"agendas": {"0": "house_rising"}})
        with self.assertRaisesRegex(ValueError, "unknown deal"):
            GameSession(Config(players=TABLE), 1, deal="nonesuch")

    def test_a_record_carries_its_deal_and_replays(self):
        session = GameSession(Config(players=TABLE), 4, deal={"deck": ["Debasement of the Coinage"]})
        prompt = session.advance()
        while prompt.kind != TURN:
            prompt = session.answer(prompt.options[0])
        session.answer(0)
        record = session.record()
        self.assertEqual(record["deal"], {"deck": ["Debasement of the Coinage"]})
        again = GameSession.replay(record)
        self.assertEqual(again.state.log, session.state.log)


class FirstGame(unittest.TestCase):
    """The first game a new player is dealt stays kind as the game changes."""

    def test_you_move_first_toward_a_house_with_two_of_it_in_hand(self):
        for seed in range(20):
            session = GameSession(Config(players=TABLE), seed, deal="first_game")
            state = session.state
            me = session.humans[0]
            self.assertEqual(state.current, me, "you move first")
            agenda = AGENDAS_BY_KEY[state.agendas[me]]
            self.assertEqual(agenda.kind, HOUSE_RISING)
            family = [state.name(u) for u in state.hands[me] if state.card(u).is_courtier and state.cstate[u].family.value == agenda.param]
            self.assertGreaterEqual(len(family), 2, family)

    def test_the_page_names_the_deal_and_table(self):
        source = (ROOT / "web" / "src" / "firstGame.ts").read_text()
        self.assertIn(f'FIRST_GAME_DEAL = "{next(k for k, v in deal.NAMED.items() if v is deal.FIRST_GAME)}"', source)
        self.assertIn('FIRST_GAME_TABLE = ["naive", "greedy", "strategic"]', source)


if __name__ == "__main__":
    unittest.main()
