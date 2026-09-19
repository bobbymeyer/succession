"""Actions and legal-move generation.

A turn is exactly one action -- play a card, make a free move, or discard --
followed by a draw. The central rule lives here: **cards from hand only ever
reach the outer circle**. An empty inner seat is filled by a free move; an
occupied one can only be taken with a promotion card.

Generated actions are fully specified (card, target courtier, target seat,
sacrifice, chosen value), so the engine never has to make a choice for a bot.
Targets that cannot do anything are not generated, so a card with no legal
target simply cannot be played that turn.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .cards import (
    EFFECT_BREAK_DEFENSE,
    EFFECT_DEMOTE,
    EFFECT_DEMOTE_AND_BREAK,
    EFFECT_INSTALL,
    EFFECT_RECALL,
    EFFECT_REMOVE,
    EFFECT_STRIP_FAITH,
)
from .enums import SEAT_ESTATE, SEATS, CardKind, Estate, Faith, Family, Seat
from .state import GameState

PLAY = "play"
MOVE = "move"
DISCARD = "discard"
PASS = "pass"


@dataclass(frozen=True, slots=True)
class Action:
    kind: str
    card: int = -1            # card uid in hand (PLAY / DISCARD)
    courtier: int = -1        # target courtier uid
    seat: Optional[Seat] = None
    player: int = -1          # target player (Outmaneuver)
    sacrifice: int = -1       # courtier card uid in hand paid as a cost
    value: str = ""           # chosen attribute value (Conversion / Adoption)

    def describe(self, state: GameState) -> str:
        if self.kind == PASS:
            return "pass"
        if self.kind == MOVE:
            return f"move {state.name(self.courtier)} -> {self.seat.value}"
        if self.kind == DISCARD:
            return f"discard {state.name(self.card)}"
        bits = [f"play {state.name(self.card)}"]
        if self.courtier >= 0:
            bits.append(f"on {state.name(self.courtier)}")
        if self.seat is not None:
            bits.append(f"into {self.seat.value}")
        if self.player >= 0:
            bits.append(f"vs P{self.player}")
        if self.sacrifice >= 0:
            bits.append(f"sacrificing {state.name(self.sacrifice)}")
        if self.value:
            bits.append(f"-> {self.value}")
        return " ".join(bits)


def _estate_matches(card_estate: Optional[Estate], estate: Estate) -> bool:
    """Wildcard cards (card_estate is None) match any estate."""

    return card_estate is None or card_estate is estate


def event_targets(state: GameState, effect: str) -> list[int]:
    """Courtiers an event of this effect can meaningfully be aimed at."""

    if effect == EFFECT_DEMOTE or effect == EFFECT_DEMOTE_AND_BREAK:
        return state.inner_uids()
    if effect in (EFFECT_REMOVE, EFFECT_RECALL):
        return state.uids_in_play()
    if effect == EFFECT_STRIP_FAITH:
        return [u for u in state.uids_in_play() if state.cstate[u].faith is not Faith.NONE]
    if effect == EFFECT_BREAK_DEFENSE:
        return [u for u in state.uids_in_play() if u in state.defenses] + [
            u for u in state.inner_uids() if u not in state.defenses
        ]
    if effect == EFFECT_INSTALL:
        empty = {SEAT_ESTATE[s] for s in state.empty_seats()}
        return [u for u in state.outer if state.cstate[u].estate in empty]
    raise ValueError(f"unknown event effect: {effect}")


def install_seat_for(state: GameState, uid: int) -> Optional[Seat]:
    """First empty seat matching a courtier's estate (Treasure Fleet / move)."""

    estate = state.cstate[uid].estate
    for seat in SEATS:
        if state.seats[seat] is None and SEAT_ESTATE[seat] is estate:
            return seat
    return None


def free_moves(state: GameState) -> list[Action]:
    """Option (b): install an outer courtier into an empty matching seat."""

    out: list[Action] = []
    for seat in state.empty_seats():
        estate = SEAT_ESTATE[seat]
        for uid in state.outer:
            if state.cstate[uid].estate is estate:
                out.append(Action(MOVE, courtier=uid, seat=seat))
    return out


def card_actions(state: GameState, player: int, uid: int) -> list[Action]:
    """Every legal way to play one card from `player`'s hand."""

    card = state.card(uid)
    kind = card.kind
    hand = state.hands[player]
    out: list[Action] = []

    if kind is CardKind.COURTIER:
        # Courtiers only ever enter the outer circle.
        return [Action(PLAY, card=uid)]

    if kind is CardKind.PROMOTION:
        for seat in state.occupied_seats():
            estate = SEAT_ESTATE[seat]
            if not _estate_matches(card.estate, estate):
                continue
            for cand in state.outer:
                if state.cstate[cand].estate is estate:
                    out.append(Action(PLAY, card=uid, courtier=cand, seat=seat))
        return out

    if kind is CardKind.DEMOTION:
        for seat in state.occupied_seats():
            if _estate_matches(card.estate, SEAT_ESTATE[seat]):
                out.append(Action(PLAY, card=uid, courtier=state.seats[seat], seat=seat))
        return out

    if kind is CardKind.REMOVAL:
        for cand in state.uids_in_play():
            if _estate_matches(card.estate, state.cstate[cand].estate):
                out.append(Action(PLAY, card=uid, courtier=cand))
        return out

    if kind is CardKind.DEFENSE:
        costs = [
            h
            for h in hand
            if h != uid
            and state.card(h).is_courtier
            and _estate_matches(card.estate, state.cstate[h].estate)
        ]
        if not costs:
            return out
        for cand in state.inner_uids():
            if cand in state.defenses:
                continue
            if state.config.defense_requires_matching_target and not _estate_matches(
                card.estate, state.cstate[cand].estate
            ):
                continue
            for cost in costs:
                out.append(Action(PLAY, card=uid, courtier=cand, sacrifice=cost))
        return out

    if kind is CardKind.STRIP:
        attribute = card.attribute
        none_value = Family.NONE if attribute == "family" else Faith.NONE
        for cand in state.uids_in_play():
            if getattr(state.cstate[cand], attribute) is not none_value:
                out.append(Action(PLAY, card=uid, courtier=cand))
        return out

    if kind is CardKind.MUTATION:
        return _mutation_actions(state, player, uid)

    if kind is CardKind.EVENT:
        for cand in event_targets(state, card.effect):
            out.append(Action(PLAY, card=uid, courtier=cand))
        return out

    if kind is CardKind.OUTMANEUVER:
        for other in range(state.config.num_players):
            if other != player and not state.skip_next[other]:
                out.append(Action(PLAY, card=uid, player=other))
        return out

    if kind is CardKind.PIVOT:
        if state.unused_agendas:
            out.append(Action(PLAY, card=uid))
        return out

    raise ValueError(f"unknown card kind: {kind}")  # pragma: no cover


def _mutation_actions(state: GameState, player: int, uid: int) -> list[Action]:
    card = state.card(uid)
    attribute = card.attribute
    hand = state.hands[player]
    out: list[Action] = []

    if attribute == "faith" and card.value is None:  # Conversion
        for cand in state.uids_in_play():
            cs = state.cstate[cand]
            if cs.mutated_faith:
                continue
            if cs.faith is Faith.OLD_GODS:
                out.append(Action(PLAY, card=uid, courtier=cand, value=Faith.MYSTERY_CULTS.value))
            elif cs.faith is Faith.MYSTERY_CULTS:
                out.append(Action(PLAY, card=uid, courtier=cand, value=Faith.OLD_GODS.value))
            else:
                # A godless or a stripped courtier comes to a faith of the
                # player's choosing.
                out.append(Action(PLAY, card=uid, courtier=cand, value=Faith.OLD_GODS.value))
                out.append(Action(PLAY, card=uid, courtier=cand, value=Faith.MYSTERY_CULTS.value))
        return out

    if attribute == "family":  # Adoption
        costs = [
            h
            for h in hand
            if h != uid
            and state.card(h).is_courtier
            and state.cstate[h].family is not Family.NONE
        ]
        for cand in state.uids_in_play():
            cs = state.cstate[cand]
            if cs.mutated_family:
                continue
            for cost in costs:
                family = state.cstate[cost].family
                if family is cs.family:
                    continue
                out.append(
                    Action(PLAY, card=uid, courtier=cand, sacrifice=cost, value=family.value)
                )
        return out

    # Estate and origin mutations have a fixed destination value.
    for cand in state.uids_in_play():
        cs = state.cstate[cand]
        if cs.mutated(attribute):
            continue
        if getattr(cs, attribute).value == card.value:
            continue
        out.append(Action(PLAY, card=uid, courtier=cand, value=card.value))
    return out


def legal_actions(state: GameState, player: int) -> list[Action]:
    """Every legal action for `player` this turn."""

    out: list[Action] = []
    for uid in state.hands[player]:
        out.extend(card_actions(state, player, uid))
    out.extend(free_moves(state))
    out.extend(Action(DISCARD, card=uid) for uid in state.hands[player])
    if not out:
        out.append(Action(PASS))
    return out
