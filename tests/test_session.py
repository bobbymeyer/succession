"""A session with people at the table plays exactly the game the simulator does."""

from __future__ import annotations

import io
import json
import random
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from succession.bots import GreedyBot, make_bot
from succession.engine import play_game
from succession.runner import main
from succession.session import COURTIER, DISCARD, HUMAN, OVER, TURN, GameSession
from succession.state import Config
from succession.terminal import play

SEEDS = range(30)


class StandIn(GreedyBot):
    """A greedy bot whose mid-card picks are the first option, and use no dice.

    A person's answer never touches the random generator, but a bot's pick
    does, so this is the one bot a scripted human can imitate exactly.
    """

    def pick_courtier(self, state, player, candidates):
        return candidates[0]

    def pick_discard(self, state, player, hand):
        return hand[0]


def stand_in_factory(tier, seat, rng):
    return StandIn(seat, rng) if tier == "stand_in" else make_bot(tier, seat, rng)


def fingerprint(state) -> tuple:
    return (
        state.turn,
        list(state.winners),
        list(state.agendas),
        state.board_summary(),
        sorted(state.stats.items()),
        list(state.log),
    )


def drive_as_stand_in(session: GameSession) -> dict:
    """Answer every human prompt the way StandIn would. Counts the prompts."""

    seen = {TURN: 0, COURTIER: 0, DISCARD: 0}
    bots = {h: StandIn(h, session.rng) for h in session.humans}
    prompt = session.advance()
    while prompt.kind != OVER:
        seen[prompt.kind] += 1
        if prompt.kind == TURN:
            action = bots[prompt.player].choose(session.state, prompt.player, prompt.options)
            prompt = session.answer(prompt.options.index(action))
        else:
            prompt = session.answer(prompt.options[0])
    return seen


class SessionMatchesSimulator(unittest.TestCase):
    def test_all_bot_session_is_play_game(self):
        for seed in SEEDS:
            config = Config(players=("naive", "greedy", "strategic", "naive"))
            reference = play_game(config, seed, make_bot, trace=True, keep_state=True)
            session = GameSession(config, seed)
            self.assertEqual(session.advance().kind, OVER)
            self.assertEqual(fingerprint(session.state), fingerprint(reference.final_state), seed)
            self.assertEqual(session.result().winners, reference.winners)

    def test_human_seat_plays_the_same_game_as_a_bot(self):
        # Same seats in the same order, so the seat shuffle puts the human
        # where the stand-in sat.
        seen = {TURN: 0, COURTIER: 0, DISCARD: 0}
        for seed in SEEDS:
            reference = play_game(
                Config(players=("stand_in", "naive", "greedy", "strategic")),
                seed,
                stand_in_factory,
                trace=True,
                keep_state=True,
            )
            session = GameSession(Config(players=(HUMAN, "naive", "greedy", "strategic")), seed)
            for kind, n in drive_as_stand_in(session).items():
                seen[kind] += n
            self.assertEqual(fingerprint(session.state), fingerprint(reference.final_state), seed)
        # The rewind-and-replay path has to have actually run for this to mean
        # anything: purges and forced discards, on the human's turn and bots'.
        self.assertGreater(seen[COURTIER], 0)
        self.assertGreater(seen[DISCARD], 0)

    def test_two_humans(self):
        for seed in range(12):
            reference = play_game(
                Config(players=("stand_in", "strategic", "stand_in")),
                seed,
                stand_in_factory,
                trace=True,
                keep_state=True,
            )
            session = GameSession(Config(players=(HUMAN, "strategic", HUMAN)), seed)
            drive_as_stand_in(session)
            self.assertEqual(fingerprint(session.state), fingerprint(reference.final_state), seed)


def random_human(session: GameSession, rng: random.Random, stop_after: int | None = None) -> None:
    prompt = session.advance()
    answered = 0
    while prompt.kind != OVER and answered != stop_after:
        if prompt.kind == TURN:
            prompt = session.answer(rng.randrange(len(prompt.options)))
        else:
            prompt = session.answer(rng.choice(prompt.options))
        answered += 1


class Records(unittest.TestCase):
    def test_a_record_replays_the_whole_game(self):
        for seed in range(15):
            session = GameSession(Config(players=(HUMAN, "naive", "greedy", "strategic")), seed)
            random_human(session, random.Random(seed))
            record = json.loads(json.dumps(session.record()))
            again = GameSession.replay(record)
            self.assertTrue(again.over)
            self.assertEqual(fingerprint(again.state), fingerprint(session.state), seed)

    def test_a_record_of_an_unfinished_game_stops_at_the_same_question(self):
        session = GameSession(Config(players=(HUMAN, "strategic", "greedy")), 11)
        random_human(session, random.Random(3), stop_after=6)
        again = GameSession.replay(json.loads(json.dumps(session.record())))
        self.assertEqual(again.prompt, session.prompt)
        self.assertEqual(fingerprint(again.state), fingerprint(session.state))

    def test_the_record_keeps_the_rules_variant(self):
        config = Config(players=(HUMAN, "naive"), faith_seats=5, house_preferred_estates=(("Mitreas", "Church"),))
        session = GameSession(config, 4)
        session.advance()
        again = GameSession.replay(json.loads(json.dumps(session.record())))
        self.assertEqual(again.config, config)


class Answers(unittest.TestCase):
    def setUp(self):
        self.session = GameSession(Config(players=(HUMAN, "naive")), 1)
        self.prompt = self.session.advance()

    def test_out_of_range_turn_choice(self):
        with self.assertRaises(ValueError):
            self.session.answer(len(self.prompt.options))
        self.assertIs(self.session.prompt, self.prompt)  # still waiting

    def test_a_card_that_was_not_offered(self):
        # Find a mid-card question and answer it with something else.
        rng = random.Random(0)
        for seed in range(200):
            session = GameSession(Config(players=(HUMAN, "naive", "naive")), seed)
            prompt = session.advance()
            while prompt.kind == TURN:
                prompt = session.answer(rng.randrange(len(prompt.options)))
            if prompt.kind in (COURTIER, DISCARD):
                bogus = next(uid for uid in range(len(session.state.cards)) if uid not in prompt.options)
                with self.assertRaises(ValueError):
                    session.answer(bogus)
                return
        self.fail("no mid-card question in 200 games")

    def test_nothing_to_answer_once_over(self):
        session = GameSession(Config(players=("naive", "naive")), 2)
        self.assertEqual(session.advance().kind, OVER)
        with self.assertRaises(ValueError):
            session.answer(0)


class Views(unittest.TestCase):
    def test_a_view_shows_only_what_the_seat_could_see(self):
        session = GameSession(Config(players=(HUMAN, "naive", "greedy", "strategic")), 9)
        prompt = session.advance()
        me = prompt.player
        view = session.view(me)
        json.dumps(view)  # it has to cross into a browser
        json.dumps(session.prompt_json())

        self.assertEqual([c["uid"] for c in view["hand"]], session.state.hands[me])
        for p in view["players"]:
            self.assertEqual(p["hand"], len(session.state.hands[p["seat"]]))
            if p["seat"] == me:
                self.assertEqual(p["agenda"]["key"], session.state.agendas[me])
            else:
                self.assertIsNone(p["agenda"])

        # No uid from anyone else's hand appears anywhere in the view.
        others = {uid for p, hand in enumerate(session.state.hands) if p != me for uid in hand}
        def uids(node):
            if isinstance(node, dict):
                if "uid" in node:
                    yield node["uid"]
                for value in node.values():
                    yield from uids(value)
            elif isinstance(node, list):
                for value in node:
                    yield from uids(value)
        self.assertFalse(others & set(uids(view)))

    def test_every_agenda_is_shown_once_it_is_over(self):
        session = GameSession(Config(players=(HUMAN, "strategic")), 5)
        random_human(session, random.Random(5))
        view = session.view(-1)
        self.assertTrue(view["over"])
        self.assertTrue(all(p["agenda"] for p in view["players"]))


class Terminal(unittest.TestCase):
    def test_a_whole_game_from_the_terminal(self):
        session = GameSession(Config(players=(HUMAN, "naive", "greedy", "strategic")), 21)
        out: list[str] = []
        self.assertTrue(play(session, read=lambda _: "1", write=out.append))
        self.assertTrue(session.over)
        self.assertIn("Game over", out[-1])

    def test_quitting_and_nonsense(self):
        answers = iter(["", "banana", "999", "q"])
        out: list[str] = []
        session = GameSession(Config(players=(HUMAN, "naive")), 3)
        self.assertFalse(play(session, read=lambda _: next(answers), write=out.append))
        self.assertEqual(sum(line.startswith("Type a number from") for line in out), 3)

    def test_record_and_replay_from_the_command_line(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "game.json"
            stdin = sys.stdin
            try:
                sys.stdin = io.StringIO("1\n2\n1\nq\n")
                with redirect_stdout(io.StringIO()) as first:
                    main(["play", "--seed", "8", "--record", str(path)])
                record = json.loads(path.read_text())
                self.assertEqual(len(record["decisions"]), 3)

                sys.stdin = io.StringIO("q\n")
                with redirect_stdout(io.StringIO()) as second:
                    main(["play", "--replay", str(path)])
            finally:
                sys.stdin = stdin
        # The replay reaches the same point: every move the first run printed
        # is in the second run's log.
        played = [line for line in first.getvalue().splitlines() if line.startswith("[t")]
        self.assertTrue(played)
        replayed = second.getvalue().splitlines()
        for line in played:
            self.assertIn(line, replayed)


if __name__ == "__main__":
    unittest.main()
