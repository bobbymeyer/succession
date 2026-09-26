"""Rule-level tests for the Court of Succession engine."""

from __future__ import annotations

import collections
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from succession.actions import DISCARD, MOVE, PASS, PLAY, Action, card_actions, legal_actions
from succession.agendas import AGENDAS_BY_KEY, satisfied
from succession.bots import make_bot
from succession.cards import build_cards
from succession.courtiers import COURTIERS, FAMILY_PREFERRED_ESTATE
from succession.engine import (
    apply_action,
    check_winners,
    draw,
    enforce_hand_limit,
    play_game,
    resolve_turn,
    setup_game,
    simulate,
)
from succession.enums import (
    FAITHS,
    SEAT_ESTATE,
    SEATS,
    CardKind,
    Estate,
    Faith,
    Family,
    Origin,
    Seat,
)
from succession.state import Config, GameState


class FixedRng:
    """A random.Random stand-in with scripted d6 rolls."""

    def __init__(self, rolls=(1,)):
        self.rolls = list(rolls)

    def randint(self, a, b):
        return self.rolls.pop(0) if self.rolls else 1

    def randrange(self, n):
        return 0

    def shuffle(self, seq):
        pass

    def choice(self, seq):
        return seq[0]


class Namers(list):
    """One purge pick per player, by name, remembering what each was offered."""

    def __init__(self, state, *names):
        super().__init__(self._Namer(self, state, name) for name in names)
        self.offered = []

    class _Namer:
        def __init__(self, owner, state, name):
            self.owner, self.uid = owner, uid(state, name)

        def pick_courtier(self, state, player, candidates):
            self.owner.offered.append(list(candidates))
            return self.uid


#: The card tests below exercise every event card, so they deal the whole
#: ten-event deck with events held in hand, as the game once played. The
#: current rules (five minor events, played when drawn) have tests of their own.
ALL_EVENTS_HELD = {"event_tiers": ("minor", "major"), "events_on_draw": False}


def fresh(**overrides) -> GameState:
    state = GameState.new(Config(**{**ALL_EVENTS_HELD, **overrides}))
    state.deck = []
    state.agendas = ["balance", "barbarian_conquest", "house_amonides", "faith_old_gods"][
        : state.config.num_players
    ]
    state.unused_agendas = [
        k for k in AGENDAS_BY_KEY if k not in state.agendas
    ]
    return state


#: A legal seven-seat court showing all three families, both faiths and a
#: barbarian -- the minimum board that satisfies Balance.
BALANCED_COURT = {
    Seat.ARCHPRIEST: "Beloved of the Gods",          # Amonides / Old Gods
    Seat.ORACLE: "Initiate of the Seven Veils",        # Mitreas / Mystery Cults
    Seat.LORD_GENERAL: "Horse Breaker",               # Argaian
    Seat.CAPTAIN_OF_THE_GUARD: "Hundred-Kill Rider",       # Barbarian
    Seat.KEEPER_OF_THE_TREASURY: "Golden Thumb",                    # Mitreas
    Seat.MASTER_OF_THE_MARKET: "Weigher of Grain",             # Amonides / Old Gods
    Seat.VOICE_OF_THE_PEOPLE: "Master Mason",                  # Barbarian
}


def fill_the_court(state: GameState) -> None:
    """Seat every empty chair from BALANCED_COURT, leaving occupied ones alone."""

    for where, name in BALANCED_COURT.items():
        if state.seats[where] is None:
            u = uid(state, name)
            if u not in state.seats.values():
                state.seats[where] = u


def judged_as(state: GameState, **overrides) -> GameState:
    """The same board, judged under a different set of rule options."""

    twin = state.clone()
    twin.config = Config(players=state.config.players, **overrides)
    return twin


def uid(state: GameState, name: str) -> int:
    for i, card in enumerate(state.cards):
        if card.name == name:
            return i
    raise KeyError(name)


def give(state: GameState, player: int, *names: str) -> list[int]:
    uids = [uid(state, n) for n in names]
    state.hands[player].extend(uids)
    return uids


def seat(state: GameState, name: str, where: Seat) -> int:
    u = uid(state, name)
    state.seats[where] = u
    return u


def outer(state: GameState, *names: str) -> list[int]:
    uids = [uid(state, n) for n in names]
    state.outer.extend(uids)
    return uids


class TestData(unittest.TestCase):
    def test_courtier_table_totals(self):
        self.assertEqual(len(COURTIERS), 40)
        faith = collections.Counter(c.faith for c in COURTIERS)
        # One cynic off the top leaves thirty-nine to split three ways.
        self.assertEqual(faith[Faith.OLD_GODS], 13)
        self.assertEqual(faith[Faith.MYSTERY_CULTS], 13)
        self.assertEqual(faith[Faith.ONE_GOD], 13)
        self.assertEqual(faith[Faith.GODLESS], 1)

    def test_one_commoner_is_born_godless(self):
        """Everyone else reaches godlessness the hard way, through Apostasy."""

        godless = [c for c in COURTIERS if c.faith is Faith.GODLESS]
        self.assertEqual([c.name for c in godless], ["The Dog of the Agora"])
        self.assertEqual(godless[0].house, "Commoner")
        self.assertIs(godless[0].estate, Estate.COMMONS)

    def test_each_faith_gets_exactly_the_same_bench(self):
        """No faith is short of candidates for any seat."""

        for faith in FAITHS:
            estates = collections.Counter(
                c.estate for c in COURTIERS if c.faith is faith
            )
            self.assertEqual(
                dict(estates),
                {Estate.CHURCH: 3, Estate.MILITARY: 4, Estate.MERCHANT: 3, Estate.COMMONS: 3},
                faith.value,
            )
        origin = collections.Counter(c.origin for c in COURTIERS)
        self.assertEqual(origin[Origin.IMPERIAL], 32)
        self.assertEqual(origin[Origin.BARBARIAN], 8)
        estate = collections.Counter(c.estate for c in COURTIERS)
        self.assertEqual(estate[Estate.MILITARY], 12)
        self.assertEqual(estate[Estate.CHURCH], 9)
        self.assertEqual(estate[Estate.MERCHANT], 9)
        self.assertEqual(estate[Estate.COMMONS], 10)
        family = collections.Counter(c.family for c in COURTIERS)
        for house in (Family.AMONIDES, Family.MITREAS, Family.ARGAIAN):
            self.assertEqual(family[house], 8)

    def test_each_house_fields_three_courtiers_in_its_own_estate(self):
        for family, estate in FAMILY_PREFERRED_ESTATE.items():
            with self.subTest(family=family.value):
                own = [c for c in COURTIERS if c.family is family and c.estate is estate]
                self.assertEqual(len(own), 3)
                other = [c for c in COURTIERS if c.family is family and c.estate is not estate]
                self.assertEqual(len(other), 5)

    def test_deck_composition(self):
        cards = build_cards(outmaneuver_copies=1)
        kinds = collections.Counter(c.kind for c in cards)
        self.assertEqual(kinds[CardKind.COURTIER], 40)
        self.assertEqual(kinds[CardKind.EVENT], 10)
        self.assertEqual(kinds[CardKind.PROMOTION], 5)
        self.assertEqual(kinds[CardKind.DEMOTION], 5)
        self.assertEqual(kinds[CardKind.REMOVAL], 6)
        self.assertEqual(kinds[CardKind.DEFENSE], 5)
        self.assertEqual(kinds[CardKind.STRIP], 2)
        self.assertEqual(kinds[CardKind.MUTATION], 9)
        self.assertEqual(kinds[CardKind.PIVOT], 1)
        self.assertEqual(kinds[CardKind.OUTMANEUVER], 1)
        self.assertEqual(len(cards), 84)

    def test_every_house_fields_one_charioteer(self):
        """A house's charioteer is its only route to the Master of the Market's seat."""

        for family in (Family.AMONIDES, Family.MITREAS, Family.ARGAIAN):
            commoners = [
                c for c in COURTIERS if c.family is family and c.estate is Estate.COMMONS
            ]
            self.assertEqual(len(commoners), 1)
            self.assertIn("Charioteer", commoners[0].name)

    def test_every_barbarian_people_appears_twice(self):
        peoples = collections.Counter(
            c.people for c in COURTIERS if c.origin is Origin.BARBARIAN
        )
        self.assertEqual(set(peoples.values()), {2})
        self.assertEqual(len(peoples), 4)


class TestHandVsPromotion(unittest.TestCase):
    def test_courtier_card_only_reaches_outer_circle(self):
        state = fresh()
        u = give(state, 0, "Beloved of the Gods")[0]
        actions = card_actions(state, 0, u)
        self.assertEqual(actions, [Action(PLAY, card=u)])
        apply_action(state, 0, actions[0], FixedRng())
        self.assertIn(u, state.outer)
        self.assertIsNone(state.seats[Seat.ARCHPRIEST])

    def test_no_action_puts_a_hand_card_into_a_seat(self):
        state = fresh()
        give(state, 0, "Beloved of the Gods", "Promotion", "Consecration")
        for action in legal_actions(state, 0):
            if action.kind == PLAY and action.seat is not None:
                # Only a promotion may name a seat, and only an occupied one.
                self.assertIsNotNone(state.seats[action.seat])

    def test_empty_seat_is_filled_by_free_move(self):
        state = fresh()
        u = outer(state, "Beloved of the Gods")[0]
        move = next(a for a in legal_actions(state, 0) if a.kind == MOVE)
        self.assertEqual(move, Action(MOVE, courtier=u, seat=Seat.ARCHPRIEST))
        apply_action(state, 0, move, FixedRng())
        self.assertEqual(state.seats[Seat.ARCHPRIEST], u)
        self.assertNotIn(u, state.outer)

    def test_move_requires_matching_estate(self):
        state = fresh()
        outer(state, "Golden Thumb")  # Merchant
        seats = {a.seat for a in legal_actions(state, 0) if a.kind == MOVE}
        self.assertEqual(seats, {Seat.KEEPER_OF_THE_TREASURY, Seat.MASTER_OF_THE_MARKET})

    def test_promotion_needs_an_occupied_seat(self):
        state = fresh()
        promo = give(state, 0, "Promotion")[0]
        outer(state, "Beloved of the Gods")
        self.assertEqual(card_actions(state, 0, promo), [])
        seat(state, "Hand of the Oracle", Seat.ARCHPRIEST)
        self.assertTrue(card_actions(state, 0, promo))

    def test_promotion_bumps_the_sitting_courtier(self):
        state = fresh()
        promo = give(state, 0, "Consecration")[0]
        sitting = seat(state, "Hand of the Oracle", Seat.ARCHPRIEST)
        climber = outer(state, "Beloved of the Gods")[0]
        action = Action(PLAY, card=promo, courtier=climber, seat=Seat.ARCHPRIEST)
        apply_action(state, 0, action, FixedRng())
        self.assertEqual(state.seats[Seat.ARCHPRIEST], climber)
        self.assertIn(sitting, state.outer)

    def test_estate_specific_promotion_only_targets_its_estate(self):
        state = fresh()
        promo = give(state, 0, "Battlefield Promotion")[0]
        seat(state, "Hand of the Oracle", Seat.ARCHPRIEST)
        seat(state, "Keeper of the Long Peace", Seat.LORD_GENERAL)
        outer(state, "Beloved of the Gods", "Crosser of Rivers")
        actions = card_actions(state, 0, promo)
        self.assertTrue(actions)
        for a in actions:
            self.assertIs(SEAT_ESTATE[a.seat], Estate.MILITARY)


class TestRemovalsAndDefenses(unittest.TestCase):
    def test_removal_takes_a_courtier_out_of_play(self):
        state = fresh()
        card = give(state, 0, "Assassination")[0]
        victim = seat(state, "Hand of the Oracle", Seat.ARCHPRIEST)
        apply_action(state, 0, Action(PLAY, card=card, courtier=victim), FixedRng())
        self.assertIsNone(state.seats[Seat.ARCHPRIEST])
        self.assertNotIn(victim, state.outer)
        self.assertIn(victim, state.discard)  # may reshuffle back as a new person

    def test_removed_out_of_game_option(self):
        state = fresh(removed_courtiers_return_to_deck=False)
        card = give(state, 0, "Assassination")[0]
        victim = outer(state, "Hand of the Oracle")[0]
        apply_action(state, 0, Action(PLAY, card=card, courtier=victim), FixedRng())
        self.assertIn(victim, state.removed)
        self.assertNotIn(victim, state.discard)

    def test_targeted_poisoning_save_on_even(self):
        state = fresh()
        card = give(state, 0, "Targeted Poisoning")[0]
        victim = outer(state, "Hand of the Oracle")[0]
        apply_action(state, 0, Action(PLAY, card=card, courtier=victim), FixedRng([4]))
        self.assertIn(victim, state.outer)  # saved

        card = give(state, 0, "Assassination")[0]
        apply_action(state, 0, Action(PLAY, card=card, courtier=victim), FixedRng([4]))
        self.assertNotIn(victim, state.outer)  # no save allowed

    def test_defense_negates_one_attack_then_is_spent(self):
        state = fresh()
        defended = seat(state, "Hand of the Oracle", Seat.ARCHPRIEST)
        cost, shield, kill1, kill2 = give(
            state, 0, "Beloved of the Gods", "Sanctuary", "Assassination", "Martyrdom"
        )
        apply_action(
            state, 0, Action(PLAY, card=shield, courtier=defended, sacrifice=cost), FixedRng()
        )
        self.assertEqual(state.defenses[defended], shield)
        self.assertIn(cost, state.discard)

        apply_action(state, 0, Action(PLAY, card=kill1, courtier=defended), FixedRng())
        self.assertEqual(state.seats[Seat.ARCHPRIEST], defended)  # negated
        self.assertNotIn(defended, state.defenses)

        apply_action(state, 0, Action(PLAY, card=kill2, courtier=defended), FixedRng())
        self.assertIsNone(state.seats[Seat.ARCHPRIEST])  # second one lands

    def test_defense_costs_a_matching_estate_courtier(self):
        state = fresh()
        seat(state, "Hand of the Oracle", Seat.ARCHPRIEST)
        shield = give(state, 0, "Bodyguard")[0]  # Military
        give(state, 0, "Beloved of the Gods")  # Church: cannot pay
        self.assertEqual(card_actions(state, 0, shield), [])
        give(state, 0, "Crosser of Rivers")  # Military: can pay
        self.assertTrue(card_actions(state, 0, shield))

    def test_patron_protection_accepts_any_estate(self):
        state = fresh()
        seat(state, "Hand of the Oracle", Seat.ARCHPRIEST)
        shield = give(state, 0, "Patron Protection")[0]
        give(state, 0, "Golden Thumb")
        self.assertTrue(card_actions(state, 0, shield))


class TestDemotionsStripsMutations(unittest.TestCase):
    def test_demotion_empties_the_seat(self):
        state = fresh()
        card = give(state, 0, "Heresy Accusation")[0]
        sitting = seat(state, "Hand of the Oracle", Seat.ARCHPRIEST)
        apply_action(
            state, 0, Action(PLAY, card=card, courtier=sitting, seat=Seat.ARCHPRIEST), FixedRng()
        )
        self.assertIsNone(state.seats[Seat.ARCHPRIEST])
        self.assertIn(sitting, state.outer)

    def test_estate_mutation_that_unmatches_a_seat_demotes(self):
        state = fresh()
        card = give(state, 0, "Enter Trade")[0]
        sitting = seat(state, "Hand of the Oracle", Seat.ARCHPRIEST)
        apply_action(
            state,
            0,
            Action(PLAY, card=card, courtier=sitting, value=Estate.MERCHANT.value),
            FixedRng(),
        )
        self.assertIsNone(state.seats[Seat.ARCHPRIEST])
        self.assertIn(sitting, state.outer)
        self.assertIs(state.cstate[sitting].estate, Estate.MERCHANT)

    def test_each_attribute_mutates_at_most_once(self):
        state = fresh()
        first, second = give(state, 0, "Take Vows", "Enter Trade")
        target = outer(state, "Crosser of Rivers")[0]
        apply_action(
            state, 0, Action(PLAY, card=first, courtier=target, value=Estate.CHURCH.value), FixedRng()
        )
        self.assertTrue(state.cstate[target].mutated_estate)
        self.assertEqual(
            [a for a in card_actions(state, 0, second) if a.courtier == target], []
        )

    def test_strip_then_conversion_restores_faith(self):
        state = fresh()
        strip, convert = give(state, 0, "Excommunication", "Conversion")
        target = outer(state, "Crosser of Rivers")[0]
        apply_action(state, 0, Action(PLAY, card=strip, courtier=target), FixedRng())
        self.assertIs(state.cstate[target].faith, Faith.NONE)
        self.assertFalse(state.cstate[target].mutated_faith)  # strips are not mutations
        options = {a.value for a in card_actions(state, 0, convert) if a.courtier == target}
        self.assertEqual(options, {f.value for f in FAITHS})
        apply_action(
            state,
            0,
            Action(PLAY, card=convert, courtier=target, value=Faith.OLD_GODS.value),
            FixedRng(),
        )
        self.assertIs(state.cstate[target].faith, Faith.OLD_GODS)

    def test_adoption_sacrifices_a_family_courtier(self):
        state = fresh()
        adopt, donor = give(state, 0, "Adoption", "Beloved of the Gods")
        target = outer(state, "Silver Tongue")[0]  # no family
        action = next(
            a for a in card_actions(state, 0, adopt) if a.courtier == target
        )
        self.assertEqual(action.sacrifice, donor)
        apply_action(state, 0, action, FixedRng())
        self.assertIs(state.cstate[target].family, Family.AMONIDES)
        self.assertIn(donor, state.discard)

    def test_castration_clears_family(self):
        state = fresh()
        card = give(state, 0, "Castration")[0]
        target = outer(state, "Beloved of the Gods")[0]
        apply_action(state, 0, Action(PLAY, card=card, courtier=target), FixedRng())
        self.assertIs(state.cstate[target].family, Family.NONE)


class TestGodlessness(unittest.TestCase):
    def test_apostasy_makes_a_courtier_godless(self):
        state = fresh()
        card = give(state, 0, "Apostasy")[0]
        target = outer(state, "Beloved of the Gods")[0]  # Old Gods
        action = next(a for a in card_actions(state, 0, card) if a.courtier == target)
        apply_action(state, 0, action, FixedRng())
        self.assertIs(state.cstate[target].faith, Faith.GODLESS)
        self.assertTrue(state.cstate[target].mutated_faith)

    def test_apostasy_cannot_target_the_godless(self):
        state = fresh()
        card = give(state, 0, "Apostasy")[0]
        target = outer(state, "The Dog of the Agora")[0]  # nothing left to lose
        self.assertEqual(
            [a for a in card_actions(state, 0, card) if a.courtier == target], []
        )

    def test_a_courtier_may_convert_or_apostatise_but_not_both(self):
        state = fresh()
        apostasy, conversion = give(state, 0, "Apostasy", "Conversion")
        target = outer(state, "Beloved of the Gods")[0]
        apply_action(
            state,
            0,
            next(a for a in card_actions(state, 0, apostasy) if a.courtier == target),
            FixedRng(),
        )
        self.assertEqual(
            [a for a in card_actions(state, 0, conversion) if a.courtier == target], []
        )

    def test_conversion_redeems_the_godless_to_any_faith(self):
        state = fresh()
        card = give(state, 0, "Conversion")[0]
        target = outer(state, "Master Swordsmith")[0]
        # Excommunication leaves the same empty slot Apostasy would, without
        # spending the courtier's one faith change.
        strip = give(state, 0, "Excommunication")[0]
        apply_action(state, 0, Action(PLAY, card=strip, courtier=target), FixedRng())
        options = {a.value for a in card_actions(state, 0, card) if a.courtier == target}
        self.assertEqual(options, {f.value for f in FAITHS})

    def test_a_godless_seat_counts_for_neither_faith(self):
        state = fresh()
        for agenda_key in ("faith_old_gods", "faith_mystery_cults"):
            agenda = AGENDAS_BY_KEY[agenda_key]
            self.assertFalse(satisfied(state, agenda))
        seat(state, "The Dog of the Agora", Seat.VOICE_OF_THE_PEOPLE)      # godless
        seat(state, "Beloved of the Gods", Seat.ARCHPRIEST)         # Old Gods
        seat(state, "Keeper of the Long Peace", Seat.LORD_GENERAL)   # Old Gods
        seat(state, "Destroyer of Walls", Seat.CAPTAIN_OF_THE_GUARD)      # Old Gods
        # Four seats are filled, but the godless one counts for nobody.
        self.assertFalse(satisfied(state, AGENDAS_BY_KEY["faith_old_gods"]))
        seat(state, "Weigher of Grain", Seat.KEEPER_OF_THE_TREASURY)               # Old Gods
        self.assertTrue(satisfied(state, AGENDAS_BY_KEY["faith_old_gods"]))

    def test_apostasy_can_deny_a_faith_its_fourth_seat(self):
        state = fresh()
        agenda = AGENDAS_BY_KEY["faith_old_gods"]
        seat(state, "Beloved of the Gods", Seat.ARCHPRIEST)
        seat(state, "Hand of the Oracle", Seat.ORACLE)
        seat(state, "Keeper of the Long Peace", Seat.LORD_GENERAL)
        victim = seat(state, "Destroyer of Walls", Seat.CAPTAIN_OF_THE_GUARD)
        self.assertTrue(satisfied(state, agenda))
        card = give(state, 0, "Apostasy")[0]
        apply_action(
            state,
            0,
            Action(PLAY, card=card, courtier=victim, value=Faith.GODLESS.value),
            FixedRng(),
        )
        self.assertFalse(satisfied(state, agenda))

    def test_a_defense_stops_apostasy(self):
        state = fresh()
        defended = seat(state, "Beloved of the Gods", Seat.ARCHPRIEST)
        cost, shield, card = give(
            state, 0, "Hand of the Oracle", "Sanctuary", "Apostasy"
        )
        apply_action(
            state, 0, Action(PLAY, card=shield, courtier=defended, sacrifice=cost), FixedRng()
        )
        apply_action(
            state,
            0,
            Action(PLAY, card=card, courtier=defended, value=Faith.GODLESS.value),
            FixedRng(),
        )
        self.assertIs(state.cstate[defended].faith, Faith.OLD_GODS)

    def test_balance_does_not_ask_for_a_godless_courtier(self):
        state = fresh()
        agenda = AGENDAS_BY_KEY["balance"]
        seat(state, "Beloved of the Gods", Seat.ARCHPRIEST)        # Amonides / Old Gods
        seat(state, "Initiate of the Seven Veils", Seat.ORACLE)      # Mitreas / Mystery
        seat(state, "Horse Breaker", Seat.LORD_GENERAL)             # Argaian / Mystery
        seat(state, "Hundred-Kill Rider", Seat.CAPTAIN_OF_THE_GUARD)     # Barbarian
        fill_the_court(state)
        self.assertTrue(satisfied(state, agenda))  # no godless courtier needed


class TestEvents(unittest.TestCase):
    """Events hit the whole table, in five minor/major pairs."""

    def play(self, state, name, rolls=(1,), player=0, deciders=None):
        card = give(state, player, name)[0]
        apply_action(state, player, Action(PLAY, card=card), FixedRng(rolls), deciders=deciders)

    def test_the_ten_events_are_five_pairs(self):
        from succession.cards import EVENT_CARDS

        self.assertEqual(len(EVENT_CARDS), 10)
        minor = [c for c in EVENT_CARDS if c.tier == "minor"]
        major = [c for c in EVENT_CARDS if c.tier == "major"]
        self.assertEqual(len(minor), 5)
        self.assertEqual(len(major), 5)
        self.assertFalse(any(c.save for c in major))
        # Only the purge has anything to save against, and only its minor half.
        self.assertEqual([c.name for c in EVENT_CARDS if c.save],
                         ["Poisoning at the Feast"])
        # Ten distinct behaviours: five effects, told apart by amount or by
        # whether a save is allowed.
        self.assertEqual(len({(c.effect, c.amount, c.save) for c in EVENT_CARDS}), 10)
        pairs = {
            ("Quarantine", "Siege"),
            ("Poisoning at the Feast", "Plague"),
            ("Caravan", "Treasure Fleet"),
            ("Debasement of the Coinage", "Famine"),
            ("Eclipse", "Meteor"),
        }
        names = {c.name for c in EVENT_CARDS}
        self.assertEqual(names, {n for pair in pairs for n in pair})

    # --- Quarantine / Siege: the freezes -----------------------------------
    def test_quarantine_seals_the_inner_circle(self):
        state = fresh()
        sitting = seat(state, "Hand of the Oracle", Seat.ARCHPRIEST)
        climber = outer(state, "Beloved of the Gods")[0]
        promo, demo = give(state, 0, "Consecration", "Heresy Accusation")
        self.assertTrue(card_actions(state, 0, promo))
        self.play(state, "Quarantine")

        self.assertTrue(state.inner_frozen)
        self.assertFalse(state.board_frozen)
        self.assertEqual(card_actions(state, 0, promo), [])
        self.assertEqual(card_actions(state, 0, demo), [])
        self.assertEqual([a for a in legal_actions(state, 1) if a.kind == MOVE], [])
        # The outer circle carries on as normal.
        courtier = give(state, 1, "Crosser of Rivers")[0]
        self.assertEqual(card_actions(state, 1, courtier), [Action(PLAY, card=courtier)])
        self.assertIn(sitting, state.seats.values())
        self.assertIn(climber, state.outer)

    def test_a_freeze_lasts_one_round(self):
        state = fresh()
        self.play(state, "Quarantine")
        self.assertTrue(state.inner_frozen)
        state.turn += state.config.num_players - 1   # the other players' turns
        self.assertTrue(state.inner_frozen)
        state.turn += 1                              # back round to the caster
        self.assertFalse(state.inner_frozen)

    def test_siege_seals_the_whole_board(self):
        state = fresh()
        seat(state, "Hand of the Oracle", Seat.ARCHPRIEST)
        outer(state, "Beloved of the Gods")
        self.play(state, "Siege")

        self.assertTrue(state.board_frozen)
        self.assertTrue(state.inner_frozen)
        for name in ("Crosser of Rivers", "Assassination", "Conversion", "Consecration"):
            card = give(state, 1, name)[0]
            self.assertEqual(card_actions(state, 1, card), [], name)
        # Cards that never touch a courtier still work.
        for name in ("Outmaneuver", "Caravan"):
            card = give(state, 1, name)[0]
            self.assertTrue(card_actions(state, 1, card), name)

    # --- Poisoning / Plague: the purges ------------------------------------
    def test_plague_lets_every_player_name_a_courtier(self):
        state = fresh()
        outer(state, "Beloved of the Gods", "Hand of the Oracle", "Golden Thumb",
              "Crosser of Rivers", "Silver Tongue")
        self.play(state, "Plague", deciders=Namers(state, "Beloved of the Gods", "Hand of the Oracle",
                                                   "Golden Thumb", "Crosser of Rivers"))
        # Four players, four names, four dead.
        self.assertEqual([state.name(u) for u in state.outer], ["Silver Tongue"])
        self.assertEqual(state.stats.get("courtiers_killed"), 4)

    def test_a_purge_is_named_all_at_once(self):
        # Everyone names against the same board, so nobody sees another's
        # pick -- and a courtier named by two dies once.
        state = fresh()
        outer(state, "Beloved of the Gods", "Hand of the Oracle", "Golden Thumb")
        namers = Namers(state, "Golden Thumb", "Golden Thumb", "Hand of the Oracle", "Golden Thumb")
        self.play(state, "Plague", deciders=namers)
        self.assertEqual([state.name(u) for u in state.outer], ["Beloved of the Gods"])
        self.assertEqual(state.stats.get("courtiers_killed"), 2)
        # Every player was offered the whole board as it stood before anyone died.
        self.assertTrue(all(len(options) == 3 for options in namers.offered))

    def test_poisoning_allows_each_target_a_save(self):
        state = fresh()
        outer(state, "Beloved of the Gods", "Hand of the Oracle", "Golden Thumb",
              "Crosser of Rivers", "Silver Tongue")
        self.play(state, "Poisoning at the Feast", rolls=(2, 2, 2, 2),  # all even
                  deciders=Namers(state, "Beloved of the Gods", "Hand of the Oracle",
                                  "Golden Thumb", "Crosser of Rivers"))
        self.assertEqual(len(state.outer), 5)
        self.assertEqual(state.stats.get("saves_made"), 4)

    # --- the caster-edge variant -------------------------------------------
    def test_caster_edge_caravan_gives_the_caster_two(self):
        state = fresh(caster_edge=True)
        state.deck = [uid(state, n) for n in ("Silver Tongue", "Golden Thumb", "Mender of Bones",
                                              "Horse Breaker", "Master Mason", "Crosser of Rivers")]
        self.play(state, "Caravan", player=1)
        self.assertEqual([len(h) for h in state.hands], [1, 2, 1, 1])

    def test_caster_edge_treasure_fleet_gives_the_caster_three(self):
        state = fresh(caster_edge=True)
        state.deck = [uid(state, n) for n in ("Silver Tongue", "Golden Thumb", "Mender of Bones",
                                              "Horse Breaker", "Master Mason", "Crosser of Rivers")]
        self.play(state, "Treasure Fleet")
        self.assertEqual([len(h) for h in state.hands], [3, 1, 1, 1])

    def test_caster_edge_famine_spares_the_caster(self):
        state = fresh(caster_edge=True)
        for p in range(4):
            give(state, p, "Assassination", "Promotion", "Demotion")
        self.play(state, "Famine")
        self.assertEqual([len(h) for h in state.hands], [3, 1, 1, 1])

    def test_caster_edge_siege_does_not_hold_its_caster(self):
        state = fresh(caster_edge=True)
        state.current = 2
        self.play(state, "Siege", player=2)
        self.assertFalse(state.board_frozen)  # the caster's own turn
        state.current = 3
        self.assertTrue(state.board_frozen)

    def test_caster_edge_plague_lets_the_caster_name_two(self):
        state = fresh(caster_edge=True)
        outer(state, "Beloved of the Gods", "Hand of the Oracle", "Golden Thumb")
        # The stand-in names the first courtier for everyone; the caster's
        # second pick is the next one.
        self.play(state, "Plague")
        self.assertEqual([state.name(u) for u in state.outer], ["Golden Thumb"])

    def test_a_forced_discard_lands_all_at_once(self):
        state = fresh()
        for p in range(4):
            give(state, p, "Assassination", "Promotion")
        seen = []

        class Watcher:
            def pick_discard(self, state, player, hand):
                seen.append(len(state.discard))
                return hand[0]

        self.play(state, "Debasement of the Coinage", deciders=[Watcher()] * 4)
        # Nobody's choice was on the pile while the others were choosing.
        self.assertEqual(seen, [0, 0, 0, 0])
        self.assertEqual(len(state.discard), 5)  # four discards and the event

    def test_a_purge_cannot_reach_a_sealed_inner_circle(self):
        state = fresh()
        sitting = seat(state, "Hand of the Oracle", Seat.ARCHPRIEST)
        outer(state, "Beloved of the Gods")
        self.play(state, "Quarantine")
        self.play(state, "Plague")
        self.assertEqual(state.seats[Seat.ARCHPRIEST], sitting)  # sealed in
        self.assertEqual(state.outer, [])                          # the rest die

    def test_a_purge_needs_somebody_to_kill(self):
        state = fresh()
        card = give(state, 0, "Plague")[0]
        self.assertEqual(card_actions(state, 0, card), [])

    # --- Caravan / Treasure Fleet: the windfalls ---------------------------
    def test_caravan_gives_every_player_a_card(self):
        state = fresh()
        state.deck = list(range(20))
        self.play(state, "Caravan")
        self.assertEqual([len(h) for h in state.hands], [1, 1, 1, 1])

    def test_treasure_fleet_gives_two(self):
        state = fresh()
        state.deck = list(range(20))
        self.play(state, "Treasure Fleet")
        self.assertEqual([len(h) for h in state.hands], [2, 2, 2, 2])

    # --- Debasement / Famine: the purses -----------------------------------
    def test_debasement_takes_a_card_from_every_hand(self):
        state = fresh()
        for p in range(4):
            give(state, p, "Assassination", "Promotion", "Demotion")
        self.play(state, "Debasement of the Coinage")
        # The caster also paid the event card itself.
        self.assertEqual([len(h) for h in state.hands], [2, 2, 2, 2])
        self.assertEqual(state.stats.get("cards_forced_out"), 4)

    def test_famine_takes_two(self):
        state = fresh()
        for p in range(4):
            give(state, p, "Assassination", "Promotion", "Demotion")
        self.play(state, "Famine")
        self.assertEqual([len(h) for h in state.hands], [1, 1, 1, 1])

    def test_an_empty_hand_has_nothing_to_give_up(self):
        state = fresh()
        give(state, 0, "Assassination")
        self.play(state, "Famine")
        self.assertEqual([len(h) for h in state.hands], [0, 0, 0, 0])

    # --- Eclipse / Meteor: the shuffles ------------------------------------
    def test_eclipse_shuffles_the_discards_back_in(self):
        state = fresh()
        state.discard = [uid(state, n) for n in ("Silver Tongue", "Golden Thumb")]
        state.deck = [uid(state, "Horse Breaker")]
        self.play(state, "Eclipse")
        self.assertEqual(state.discard, [uid(state, "Eclipse")])  # only the card itself
        self.assertEqual(len(state.deck), 3)

    def test_meteor_shuffles_every_hand_in_and_deals_back(self):
        state = fresh()
        state.deck = [uid(state, n) for n in
                      ("Silver Tongue", "Golden Thumb", "Horse Breaker", "Mender of Bones")]
        give(state, 1, "Assassination", "Promotion")
        give(state, 2, "Demotion")
        before = [len(h) for h in state.hands]
        self.play(state, "Meteor")
        after = [len(h) for h in state.hands]
        self.assertEqual(after[1:], before[1:])      # sizes are preserved
        self.assertEqual(sum(after), sum(before))
        everywhere = [u for h in state.hands for u in h] + state.deck
        self.assertEqual(len(everywhere), len(set(everywhere)))

    def test_no_defense_stops_an_event(self):
        state = fresh()
        defended = seat(state, "Hand of the Oracle", Seat.ARCHPRIEST)
        cost, shield = give(state, 0, "Beloved of the Gods", "Sanctuary")
        apply_action(
            state, 0, Action(PLAY, card=shield, courtier=defended, sacrifice=cost), FixedRng()
        )
        self.play(state, "Plague")
        self.assertIn(defended, state.discard)
        self.assertIn(shield, state.discard)


class TestOutmaneuverAndPivot(unittest.TestCase):
    def test_outmaneuver_skips_the_target_player(self):
        state = fresh()
        card = give(state, 0, "Outmaneuver")[0]
        apply_action(state, 0, Action(PLAY, card=card, player=2), FixedRng())
        self.assertTrue(state.skip_next[2])
        # It cannot be stacked on an already-skipping player.
        card2 = give(state, 0, "Outmaneuver")[0]
        self.assertNotIn(2, [a.player for a in card_actions(state, 0, card2)])

    def test_outmaneuver_costs_the_target_a_turn(self):
        """A stalled player's whole turn is consumed, action and draw alike."""

        class Staller:
            """Plays Outmaneuver whenever it can, and discards otherwise."""

            observes = False

            def __init__(self, seat, rng):
                self.seat = seat

            def choose(self, state, player, actions):
                for action in actions:
                    if action.kind == PLAY and action.player >= 0:
                        return action
                return next(a for a in actions if a.kind == DISCARD)

        result = play_game(
            Config(max_turns=80, **ALL_EVENTS_HELD),
            seed=4,
            bot_factory=lambda tier, seat, rng: Staller(seat, rng),
            keep_state=True,
        )
        self.assertGreaterEqual(result.stats.get("turns_skipped", 0), 1)
        self.assertGreaterEqual(result.stats.get("played_outmaneuver", 0), 1)

    def test_pivot_swaps_the_agenda(self):
        state = fresh()
        card = give(state, 0, "Schismatic Event")[0]
        old = state.agendas[0]
        pool = list(state.unused_agendas)
        apply_action(state, 0, Action(PLAY, card=card), FixedRng())
        self.assertNotEqual(state.agendas[0], old)
        self.assertIn(state.agendas[0], pool)
        self.assertIn(old, state.unused_agendas)
        self.assertEqual(len(state.unused_agendas), len(pool))


class TestWinConditions(unittest.TestCase):
    def test_house_rising_needs_three_seats_including_its_own_estate(self):
        state = fresh()
        agenda = AGENDAS_BY_KEY["house_amonides"]           # Amonides: Church
        seat(state, "Beloved of the Gods", Seat.ARCHPRIEST)   # Church
        seat(state, "Keeper of the Long Peace", Seat.LORD_GENERAL)
        self.assertFalse(satisfied(state, agenda))          # only two seats
        seat(state, "Weigher of Grain", Seat.KEEPER_OF_THE_TREASURY)
        self.assertTrue(satisfied(state, agenda))

    def test_house_rising_rejects_a_trio_outside_its_own_estate(self):
        state = fresh()
        agenda = AGENDAS_BY_KEY["house_amonides"]           # Amonides: Church
        seat(state, "Keeper of the Long Peace", Seat.LORD_GENERAL)     # Military
        seat(state, "Speaker of the Old Words", Seat.CAPTAIN_OF_THE_GUARD)  # Military
        seat(state, "Weigher of Grain", Seat.KEEPER_OF_THE_TREASURY)                 # Merchant
        self.assertFalse(satisfied(state, agenda))  # three seats, no Church seat
        # ...but they do win under --house-any-three.
        self.assertTrue(
            satisfied(judged_as(state, house_rising_requires_preferred_seat=False), agenda)
        )
        seat(state, "Beloved of the Gods", Seat.ARCHPRIEST)
        self.assertTrue(satisfied(state, agenda))

    def test_house_rising_counts_only_the_named_family(self):
        state = fresh()
        agenda = AGENDAS_BY_KEY["house_amonides"]
        seat(state, "Beloved of the Gods", Seat.ARCHPRIEST)
        seat(state, "Initiate of the Seven Veils", Seat.ORACLE)   # Mitreas
        seat(state, "Horse Breaker", Seat.LORD_GENERAL)          # Argaian
        self.assertFalse(satisfied(state, agenda))

    def test_each_house_has_its_own_estate_to_claim(self):
        """Amonides/Church, Mitreas/Merchant, Argaian/Military all work."""

        for family, names in (
            ("Amonides", ("Beloved of the Gods", "Keeper of the Long Peace", "Weigher of Grain")),
            ("Mitreas", ("Golden Thumb", "Crosser of Rivers", "Initiate of the Seven Veils")),
            ("Argaian", ("Horse Breaker", "Reader of Omens", "Founder of Markets")),
        ):
            with self.subTest(family=family):
                state = fresh()
                agenda = AGENDAS_BY_KEY[f"house_{family.lower()}"]
                estate = FAMILY_PREFERRED_ESTATE[Family(family)]
                for name in names:
                    spot = next(
                        s
                        for s in SEATS
                        if state.seats[s] is None
                        and SEAT_ESTATE[s] is state.cstate[uid(state, name)].estate
                    )
                    state.seats[spot] = uid(state, name)
                self.assertTrue(satisfied(state, agenda))
                held = [
                    s
                    for s in SEATS
                    if state.seats[s] is not None and SEAT_ESTATE[s] is estate
                ]
                self.assertTrue(held, f"{family} took no {estate.value} seat")

    def test_a_preferred_estate_override_changes_which_seat_counts(self):
        state = fresh(house_preferred_estates=(("Amonides", "Merchant"),))
        agenda = AGENDAS_BY_KEY["house_amonides"]
        seat(state, "Beloved of the Gods", Seat.ARCHPRIEST)            # Church
        seat(state, "Hand of the Oracle", Seat.ORACLE)                   # Church
        seat(state, "Keeper of the Long Peace", Seat.LORD_GENERAL)      # Military
        self.assertFalse(satisfied(state, agenda))  # no Merchant seat held
        self.assertTrue(satisfied(judged_as(state), agenda))  # Church by default
        state.seats[Seat.LORD_GENERAL] = None
        seat(state, "Weigher of Grain", Seat.KEEPER_OF_THE_TREASURY)
        self.assertTrue(satisfied(state, agenda))

    def test_faith_ascendant_needs_four_seats(self):
        state = fresh()
        agenda = AGENDAS_BY_KEY["faith_mystery_cults"]
        seat(state, "Initiate of the Seven Veils", Seat.ARCHPRIEST)
        seat(state, "Whisperer to the Serpent", Seat.ORACLE)
        seat(state, "Crosser of Rivers", Seat.LORD_GENERAL)
        seat(state, "Rider of the Long Road", Seat.CAPTAIN_OF_THE_GUARD)
        self.assertTrue(satisfied(state, agenda))

    def test_barbarian_conquest_wins_on_three_seated_barbarians(self):
        state = fresh()
        agenda = AGENDAS_BY_KEY["barbarian_conquest"]
        seat(state, "Priest of the Two-Horned God", Seat.ARCHPRIEST)
        seat(state, "Caravan-Lord of the Salt Road", Seat.KEEPER_OF_THE_TREASURY)
        self.assertFalse(satisfied(state, agenda))
        seat(state, "Master Mason", Seat.VOICE_OF_THE_PEOPLE)
        self.assertTrue(satisfied(state, agenda))
        # A variant asks for four.
        self.assertFalse(satisfied(judged_as(state, conquest_barbarians=4), agenda))
        seat(state, "Hundred-Kill Rider", Seat.LORD_GENERAL)
        self.assertTrue(satisfied(judged_as(state, conquest_barbarians=4), agenda))

    def test_barbarian_conquest_has_no_generals_shortcut(self):
        """Holding both Military seats with barbarians is only two of the three."""

        state = fresh()
        agenda = AGENDAS_BY_KEY["barbarian_conquest"]
        seat(state, "Cataphract of the Iron Bridge", Seat.LORD_GENERAL)
        seat(state, "Hundred-Kill Rider", Seat.CAPTAIN_OF_THE_GUARD)
        self.assertFalse(satisfied(state, agenda))
        seat(state, "Master Mason", Seat.VOICE_OF_THE_PEOPLE)
        self.assertTrue(satisfied(state, agenda))

    def test_barbarian_conquest_ignores_the_outer_circle(self):
        state = fresh()
        agenda = AGENDAS_BY_KEY["barbarian_conquest"]
        outer(state, "Master Mason", "Priest of the Two-Horned God", "Hundred-Kill Rider")
        self.assertFalse(satisfied(state, agenda))

    def test_balance_needs_every_family_both_faiths_and_a_barbarian(self):
        state = fresh()
        agenda = AGENDAS_BY_KEY["balance"]
        seat(state, "Beloved of the Gods", Seat.ARCHPRIEST)          # Amonides / Old Gods
        seat(state, "Initiate of the Seven Veils", Seat.ORACLE)        # Mitreas / Mystery
        seat(state, "Horse Breaker", Seat.LORD_GENERAL)               # Argaian / Mystery
        self.assertFalse(satisfied(state, agenda))
        seat(state, "Hundred-Kill Rider", Seat.CAPTAIN_OF_THE_GUARD)       # Barbarian
        self.assertFalse(satisfied(state, agenda))  # diverse, but a thin court
        fill_the_court(state)
        self.assertTrue(satisfied(state, agenda))

    def test_balance_wants_a_full_court(self):
        """A diverse court with an empty chair is not a balanced one."""

        state = fresh()
        agenda = AGENDAS_BY_KEY["balance"]
        fill_the_court(state)
        self.assertTrue(satisfied(state, agenda))
        # Every seat is wanted; the old rule allowed one empty chair.
        state.seats[Seat.MASTER_OF_THE_MARKET] = None
        self.assertFalse(satisfied(state, agenda))
        self.assertTrue(satisfied(judged_as(state, balance_seats=6), agenda))
        state.seats[Seat.ORACLE] = None
        self.assertFalse(satisfied(judged_as(state, balance_seats=6), agenda))

    def test_simultaneous_agendas_both_win(self):
        state = fresh()
        state.agendas = ["faith_mystery_cults", "house_mitreas", "barbarian_conquest", "balance"]
        seat(state, "Initiate of the Seven Veils", Seat.ARCHPRIEST)
        seat(state, "Rider of the Long Road", Seat.CAPTAIN_OF_THE_GUARD)
        seat(state, "Crosser of Rivers", Seat.LORD_GENERAL)
        seat(state, "Golden Thumb", Seat.KEEPER_OF_THE_TREASURY)  # Mitreas' own estate
        self.assertEqual(check_winners(state), [0, 1])


class TestDeckAndTurns(unittest.TestCase):
    def test_empty_deck_reshuffles_the_discard(self):
        state = fresh()
        state.deck = []
        state.discard = [uid(state, "Silver Tongue"), uid(state, "Golden Thumb")]
        draw(state, 0, random.Random(0))
        self.assertEqual(len(state.hands[0]), 1)
        self.assertEqual(state.reshuffles, 1)

    def test_a_draw_is_never_capped(self):
        # The limit is checked as a turn ends, not when cards come in.
        state = fresh(hand_limit=3)
        state.deck = [uid(state, n) for n in ("Silver Tongue", "Golden Thumb", "Mender of Bones", "Horse Breaker")]
        draw(state, 0, random.Random(0), count=4)
        self.assertEqual(len(state.hands[0]), 4)

    def test_the_old_rule_caps_the_draw(self):
        state = fresh(hand_limit=3, hand_limit_at_end_of_turn=False)
        state.deck = [uid(state, n) for n in ("Silver Tongue", "Golden Thumb", "Mender of Bones", "Horse Breaker")]
        draw(state, 0, random.Random(0), count=4)
        self.assertEqual(len(state.hands[0]), 3)

    def test_a_turn_ends_by_discarding_down_to_the_limit(self):
        state = fresh(hand_limit=3)
        names = ("Silver Tongue", "Golden Thumb", "Mender of Bones", "Horse Breaker", "Master Mason")
        state.hands[0] = [uid(state, n) for n in names]
        state.hands[1] = [uid(state, n) for n in ("Crosser of Rivers", "Buyer of Cities", "Reader of Omens", "Hundred-Kill Rider")]

        class Chooser:
            def __init__(self):
                self.asked = []

            def pick_discard(self, state, player, hand):
                self.asked.append(list(hand))
                return hand[-1]

        mine = Chooser()
        # Only the player whose turn is ending discards; the other overfull
        # hand waits for its own turn.
        resolve_turn(state, 0, Action(PASS, 0), random.Random(0), [mine, Chooser(), Chooser(), Chooser()])
        self.assertEqual([state.name(u) for u in state.hands[0]], list(names[:3]))
        self.assertEqual([state.name(u) for u in state.discard], ["Master Mason", "Horse Breaker"])
        self.assertEqual(len(mine.asked), 2)
        self.assertEqual(len(state.hands[1]), 4)

    def test_the_old_rule_never_discards_to_the_limit(self):
        state = fresh(hand_limit=3, hand_limit_at_end_of_turn=False)
        state.hands[0] = [uid(state, n) for n in ("Silver Tongue", "Golden Thumb", "Mender of Bones", "Horse Breaker")]
        enforce_hand_limit(state, 0, None)
        self.assertEqual(len(state.hands[0]), 4)

    def test_events_on_draw_play_at_once_and_are_replaced(self):
        # Variant: a drawn event resolves for whoever drew it, goes to the
        # discard, and the drawer draws again.
        state = fresh(events_on_draw=True)
        state.deck = [uid(state, "Golden Thumb"), uid(state, "Siege")]  # Siege on top
        draw(state, 0, random.Random(0))
        self.assertEqual([state.name(u) for u in state.hands[0]], ["Golden Thumb"])
        self.assertEqual([state.name(u) for u in state.discard], ["Siege"])
        self.assertTrue(state.board_frozen)

    def test_minor_events_on_draw_leaves_the_majors_in_hand(self):
        state = fresh(events_on_draw=True, events_on_draw_minor_only=True)
        state.deck = [uid(state, n) for n in ("Golden Thumb", "Siege", "Quarantine")]  # Quarantine on top
        draw(state, 0, random.Random(0), count=2)
        self.assertEqual([state.name(u) for u in state.hands[0]], ["Siege", "Golden Thumb"])
        self.assertEqual([state.name(u) for u in state.discard], ["Quarantine"])
        self.assertTrue(state.inner_frozen)

    def test_the_deck_holds_the_five_minor_events_played_when_drawn(self):
        from succession.cards import EVENT_CARDS

        config = Config()
        self.assertTrue(config.events_on_draw)
        state = GameState.new(config)
        events = sorted(c.name for c in state.cards if c.kind.value == "Event")
        self.assertEqual(events, sorted(c.name for c in EVENT_CARDS if c.tier == "minor"))
        self.assertEqual(len(state.cards), 79)

    def test_either_half_of_the_events_can_be_left_out(self):
        from succession.cards import EVENT_CARDS

        for tier in ("minor", "major"):
            state = GameState.new(Config(event_tiers=(tier,)))
            names = {c.name for c in state.cards}
            self.assertEqual(len(state.cards), 79)
            for c in EVENT_CARDS:
                self.assertEqual(c.name in names, c.tier == tier)

    def test_events_on_draw_never_deals_an_event_into_a_starting_hand(self):
        from succession.enums import CardKind

        for seed in range(20):
            state = setup_game(Config(events_on_draw=True), random.Random(seed))
            for hand in state.hands:
                self.assertEqual(len(hand), state.config.starting_hand)
                self.assertFalse(any(state.card(u).kind is CardKind.EVENT for u in hand))
            self.assertEqual(state.discard, [])

    def test_exhausted_deck_and_discard_is_not_an_error(self):
        state = fresh()
        state.deck = []
        state.discard = []
        draw(state, 0, random.Random(0))
        self.assertEqual(state.hands[0], [])

    def test_setup_deals_one_private_agenda_per_player(self):
        config = Config()
        state = setup_game(config, random.Random(1))
        self.assertEqual(len(state.agendas), config.num_players)
        self.assertEqual(len(set(state.agendas)), config.num_players)
        self.assertEqual(len(state.unused_agendas), len(AGENDAS_BY_KEY) - config.num_players)
        for hand in state.hands:
            self.assertEqual(len(hand), config.starting_hand)

    def test_excluded_agendas_never_reach_the_table(self):
        config = Config(excluded_agendas=("balance",))
        for seed in range(20):
            state = setup_game(config, random.Random(seed))
            self.assertNotIn("balance", state.agendas)
            self.assertNotIn("balance", state.unused_agendas)
            self.assertEqual(
                len(state.agendas) + len(state.unused_agendas), len(AGENDAS_BY_KEY) - 1
            )

    def test_excluding_too_many_agendas_is_an_error(self):
        config = Config(excluded_agendas=tuple(list(AGENDAS_BY_KEY)[:5]))
        with self.assertRaises(ValueError):
            setup_game(config, random.Random(0))

    def test_the_draw_comes_before_the_action(self):
        """A card picked up at the top of the turn is playable that turn."""

        seen = []

        class Watcher:
            observes = False

            def __init__(self, seat, rng):
                self.rng = rng

            def choose(self, state, player, actions):
                seen.append(len(state.hands[player]))
                return next(a for a in actions if a.kind == DISCARD)

        # Without Discard & Draw, so the discards do not refill the hand.
        config = Config(max_turns=8, discard_draws=False, **ALL_EVENTS_HELD)
        play_game(config, seed=1, bot_factory=lambda t, s, r: Watcher(s, r))
        # Dealt five, drew a sixth before being asked to act.
        self.assertEqual(seen[0], config.starting_hand + 1)
        self.assertTrue(all(n == config.starting_hand + 1 for n in seen))

    def test_one_card_leaves_the_deck_per_turn_taken(self):
        """The draw is the first thing a turn does, and the only one it does."""

        class Discarder:
            observes = False

            def __init__(self, seat, rng):
                self.rng = rng

            def choose(self, state, player, actions):
                return next(a for a in actions if a.kind == DISCARD)

        config = Config(max_turns=10, discard_draws=False, **ALL_EVENTS_HELD)
        result = play_game(
            config, seed=1, bot_factory=lambda t, s, r: Discarder(s, r), keep_state=True
        )
        state = result.final_state
        dealt = config.starting_hand * config.num_players
        self.assertEqual(len(state.deck), len(state.cards) - dealt - result.turns)

    def test_discard_and_draw_keeps_the_hand_whole(self):
        """A turn spent discarding draws a replacement straight away."""

        state = setup_game(Config(), random.Random(3))
        player = state.current
        draw(state, player, random.Random(0))  # the top-of-turn draw
        hand_before = list(state.hands[player])
        deck_top = state.deck[-1]
        thrown = hand_before[0]
        apply_action(state, player, Action(DISCARD, card=thrown), random.Random(0))
        self.assertEqual(len(state.hands[player]), len(hand_before))
        self.assertNotIn(thrown, state.hands[player])
        self.assertEqual(state.discard[-1], thrown)
        self.assertIn(deck_top, state.hands[player])  # the replacement is the top card

    def test_two_cards_leave_the_deck_per_discard_turn(self):
        class Discarder:
            observes = False

            def __init__(self, seat, rng):
                self.rng = rng

            def choose(self, state, player, actions):
                return next(a for a in actions if a.kind == DISCARD)

        config = Config(max_turns=4, **ALL_EVENTS_HELD)
        result = play_game(config, seed=1, bot_factory=lambda t, s, r: Discarder(s, r), keep_state=True)
        dealt = config.starting_hand * config.num_players
        # One at the top of each turn, one to replace each discard.
        self.assertEqual(len(result.final_state.deck), len(result.final_state.cards) - dealt - 2 * result.turns)

    def test_a_bots_lookahead_does_not_draw_the_replacement(self):
        """The replacement is hidden: a lookahead must not see the deck's top."""

        state = setup_game(Config(), random.Random(3))
        player = state.current
        thrown = state.hands[player][0]
        after = simulate(state, player, Action(DISCARD, card=thrown))
        self.assertEqual(len(after.hands[player]), len(state.hands[player]) - 1)
        self.assertEqual(after.deck, state.deck)

    def test_the_move_is_called_discard_and_draw(self):
        state = setup_game(Config(), random.Random(3))
        uid = state.hands[state.current][0]
        self.assertEqual(Action(DISCARD, card=uid).describe(state), f"discard & draw: {state.name(uid)}")
        plain = setup_game(Config(discard_draws=False), random.Random(3))
        self.assertEqual(Action(DISCARD, card=uid).describe(plain), f"discard {plain.name(uid)}")

    def test_a_player_always_has_a_legal_action(self):
        state = setup_game(Config(), random.Random(5))
        for p in range(state.config.num_players):
            self.assertTrue(legal_actions(state, p))


class TestEventValuation(unittest.TestCase):
    """The heuristics are simulation scaffolding, so pin their direction.

    None of this is a rule. What these check is that a thinking bot wants an
    event in the situation the card is for, and does not want it otherwise.
    """

    def setUp(self):
        self.bot = make_bot("strategic", 0, random.Random(0))

    def event(self, name):
        from succession.cards import EVENT_CARDS

        return next(c for c in EVENT_CARDS if c.name == name)

    def test_a_freeze_is_worth_more_when_there_is_a_lead_to_protect(self):
        state = fresh()
        siege = self.event("Siege")
        behind = self.bot.event_bonus(state, 0, siege, progress=0.2)
        ahead = self.bot.event_bonus(state, 0, siege, progress=0.9)
        self.assertEqual(behind, 0.0)
        self.assertGreater(ahead, 0.0)

    def test_a_siege_is_worth_more_than_a_quarantine(self):
        state = fresh()
        self.assertGreater(
            self.bot.event_bonus(state, 0, self.event("Siege"), progress=0.9),
            self.bot.event_bonus(state, 0, self.event("Quarantine"), progress=0.9),
        )

    def test_a_table_wide_discard_is_for_when_our_own_hand_is_dead(self):
        """Everyone loses the same count, so only our own junk tips it."""

        famine = self.event("Famine")
        live = fresh()
        give(live, 0, "Beloved of the Gods", "Golden Thumb", "Horse Breaker")
        dead = fresh()
        # Promotions and demotions with an empty board can do nothing at all.
        give(dead, 0, "Promotion", "Demotion", "Heresy Accusation")
        self.assertGreater(
            self.bot.event_bonus(dead, 0, famine, progress=0.3),
            self.bot.event_bonus(live, 0, famine, progress=0.3),
        )

    def test_famine_is_worth_more_than_debasement_on_the_same_hand(self):
        state = fresh()
        give(state, 0, "Promotion", "Demotion")
        self.assertGreater(
            self.bot.event_bonus(state, 0, self.event("Famine"), progress=0.3),
            self.bot.event_bonus(state, 0, self.event("Debasement of the Coinage"), progress=0.3),
        )

    def test_a_reshuffle_is_for_when_the_deck_is_running_out(self):
        eclipse = self.event("Eclipse")
        full = fresh()
        full.deck = list(range(30))
        full.discard = [uid(full, "Silver Tongue")]
        empty = fresh()
        empty.deck = []
        empty.discard = [uid(empty, "Silver Tongue")]
        self.assertGreater(
            self.bot.event_bonus(empty, 0, eclipse, progress=0.3),
            self.bot.event_bonus(full, 0, eclipse, progress=0.3),
        )

    def test_hand_edge_rises_with_a_bigger_hand_than_the_table(self):
        state = fresh()
        thin = self.bot.hand_edge(state, 0)
        give(state, 0, "Assassination", "Promotion", "Demotion")
        self.assertGreater(self.bot.hand_edge(state, 0), thin)

    def test_hand_edge_stays_small_against_a_board_move(self):
        """Cards win games by becoming seats, so they must not outrank one."""

        state = fresh()
        for p in range(4):
            give(state, p, "Assassination", "Promotion")
        give(state, 0, "Demotion", "Castration", "Conversion")
        self.assertLess(abs(self.bot.hand_edge(state, 0)), 0.05)

    def test_a_bot_models_its_own_purge_pick_as_a_good_one(self):
        """Our choice in a purge is ours; the stand-in picks arbitrarily."""

        state = fresh()
        outer(state, "Beloved of the Gods", "Hand of the Oracle", "Golden Thumb",
              "Crosser of Rivers", "Silver Tongue")
        card = give(state, 0, "Plague")[0]
        action = Action(PLAY, card=card)
        mine = simulate(state, 0, action, decider=self.bot)
        theirs = simulate(state, 0, action)
        # The stand-in names the first courtier for everyone, and one named
        # four times dies once; the bot's own pick is its own.
        self.assertEqual(len(theirs.outer), 4)
        self.assertIn(len(mine.outer), (3, 4))
        self.assertIsNotNone(self.bot.pick_courtier(state, 0, state.outer))


class TestGames(unittest.TestCase):
    def test_games_terminate_and_are_reproducible(self):
        config = Config(max_turns=600)
        first = play_game(config, seed=11, bot_factory=make_bot)
        again = play_game(config, seed=11, bot_factory=make_bot)
        self.assertEqual(first.turns, again.turns)
        self.assertEqual(first.winners, again.winners)
        self.assertEqual(first.board, again.board)

    def test_batch_of_games_mostly_resolves(self):
        config = Config(max_turns=600)
        results = [play_game(config, seed=s, bot_factory=make_bot) for s in range(40)]
        self.assertTrue(all(r.turns <= config.max_turns for r in results))
        self.assertGreater(sum(1 for r in results if r.winners), 35)
        for r in results:
            for p in r.winners:
                self.assertIn(r.agendas[p], AGENDAS_BY_KEY)

    def test_all_tier_combinations_play(self):
        for tiers in (
            ("naive", "naive"),
            ("greedy", "greedy", "greedy"),
            ("strategic", "strategic", "strategic", "strategic"),
            ("naive", "greedy", "strategic"),
        ):
            with self.subTest(tiers=tiers):
                result = play_game(Config(players=tiers, max_turns=400), seed=3, bot_factory=make_bot)
                self.assertLessEqual(result.turns, 400)

    def test_board_invariants_hold_through_a_game(self):
        result = play_game(Config(max_turns=400), seed=21, bot_factory=make_bot, keep_state=True)
        state = result.final_state
        for s, u in state.seats.items():
            if u is not None:
                self.assertIs(state.cstate[u].estate, SEAT_ESTATE[s])
        everywhere = (
            state.deck
            + state.discard
            + state.outer
            + state.removed
            + [u for u in state.seats.values() if u is not None]
            + [u for hand in state.hands for u in hand]
            + list(state.defenses.values())  # attachments sit face-up on the table
        )
        self.assertEqual(len(everywhere), len(state.cards))
        self.assertEqual(len(set(everywhere)), len(state.cards))


if __name__ == "__main__":
    unittest.main(verbosity=2)
