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
    EFFECT_DISCARD_ALL,
    EFFECT_DRAW_ALL,
    EFFECT_PURGE,
    EFFECT_REDEAL,
    EFFECT_RESHUFFLE,
)
from .enums import FAITHS, SEAT_ESTATE, CardKind, Estate, Faith, Family, Seat
from .state import GameState

#: Kinds a Siege stops outright -- anything that moves a courtier or changes one.
FROZEN_BY_SIEGE = frozenset({
    CardKind.COURTIER, CardKind.PROMOTION, CardKind.DEMOTION, CardKind.REMOVAL,
    CardKind.DEFENSE, CardKind.STRIP, CardKind.MUTATION,
})
#: Kinds a Quarantine stops: everything that reaches into an inner seat.
FROZEN_BY_QUARANTINE = frozenset({
    CardKind.PROMOTION, CardKind.DEMOTION, CardKind.DEFENSE,
})

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


def event_is_playable(state: GameState, player: int, effect: str) -> bool:
    """Events hit the whole table, so they only need something to act on."""

    if effect == EFFECT_PURGE:
        return bool(purge_targets(state)) and not state.board_frozen
    if effect == EFFECT_DRAW_ALL:
        return bool(state.deck or state.discard)
    if effect == EFFECT_DISCARD_ALL:
        return any(state.hands)
    if effect == EFFECT_RESHUFFLE:
        return bool(state.discard)
    if effect == EFFECT_REDEAL:
        return any(state.hands)
    return True  # the two freezes are always worth playing


def purge_targets(state: GameState) -> list[int]:
    """Courtiers a purge may kill: the whole board, or only the outer circle
    while the inner one is sealed."""

    return state.outer[:] if state.inner_frozen else state.uids_in_play()


def _touchable(state: GameState) -> list[int]:
    """Courtiers a card may reach: not the seated ones while a freeze holds."""

    return state.outer[:] if state.inner_frozen else state.uids_in_play()


def free_moves(state: GameState) -> list[Action]:
    """Option (b): install an outer courtier into an empty matching seat."""

    if state.inner_frozen:
        return []
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

    # A siege stops every courtier in place; a quarantine seals the seats only.
    if state.board_frozen and kind in FROZEN_BY_SIEGE:
        return out
    if state.inner_frozen and kind in FROZEN_BY_QUARANTINE:
        return out

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
        for cand in _touchable(state):
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
        for cand in _touchable(state):
            if getattr(state.cstate[cand], attribute) is not none_value:
                out.append(Action(PLAY, card=uid, courtier=cand))
        return out

    if kind is CardKind.MUTATION:
        return _mutation_actions(state, player, uid)

    if kind is CardKind.EVENT:
        if event_is_playable(state, player, card.effect):
            out.append(Action(PLAY, card=uid))
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
        # Any faith but the one they already hold. A godless or excommunicated
        # courtier can be brought to any of the three.
        for cand in _touchable(state):
            cs = state.cstate[cand]
            if cs.mutated_faith:
                continue
            for faith in FAITHS:
                if faith is not cs.faith:
                    out.append(Action(PLAY, card=uid, courtier=cand, value=faith.value))
        return out

    if attribute == "family":  # Adoption
        costs = [
            h
            for h in hand
            if h != uid
            and state.card(h).is_courtier
            and state.cstate[h].family is not Family.NONE
        ]
        for cand in _touchable(state):
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
    for cand in _touchable(state):
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
