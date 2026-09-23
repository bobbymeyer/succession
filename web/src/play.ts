// Playing by hand: click a card to pick it up, or drag it where it goes.
//
// Like moves.ts, this knows no rules. It reads the engine's list of legal
// actions and says, for the selection so far, what is lit up and what each
// click or drop would select. A selection that pins down one action is played
// at once; anything short of that waits for the next click.
//
//   nothing picked up     every card with a move is lit; click one to pick it up
//   a card picked up      its buttons (Play, Discard & Draw) sit over it; the
//                         courtiers and players it can target are lit; click
//                         it again to put it down
//   a courtier picked up  the empty seats it can move into are lit
//   part-way through      whatever the action still needs is lit: a seat, a
//                         courtier to pay with, a player, or a value to choose

import { build, type Selection } from "./moves";
import type { Action } from "./protocol";

/** A button over the card that is picked up. */
export interface Offer {
  label: string;
  selection: Selection;
}

/** What the player is choosing now, for the instruction line. */
export type Step = "start" | "card" | "mover" | "courtier" | "seat" | "sacrifice" | "target_player" | "value" | "done";

export interface Stage {
  step: Step;
  /** The card (hand card or moving courtier) picked up, if any. */
  active: number | null;
  offers: Offer[];
  /** Lit cards, and what clicking each selects ({} puts everything down). */
  cards: Map<number, Selection>;
  seats: Map<string, Selection>;
  players: Map<number, Selection>;
}

const PUT_DOWN: Selection = {};

function isEmpty(selection: Selection): boolean {
  return Object.keys(selection).length === 0;
}

/** Only the card chosen so far: the card was clicked and nothing else. */
function onlyCard(selection: Selection): boolean {
  return Object.keys(selection).length === 1 && typeof selection.card === "number";
}

function isMover(selection: Selection): boolean {
  return selection.kind === "move" && Object.keys(selection).length === 3 && typeof selection.courtier === "number";
}

/** Picking up a hand card: every hand card with a move. */
function pickUps(actions: Action[]): Map<number, Selection> {
  const cards = new Map<number, Selection>();
  for (const a of actions) {
    if (a.card !== null) cards.set(a.card, { card: a.card });
    else if (a.kind === "move" && a.courtier !== null) cards.set(a.courtier, { card: null, kind: "move", courtier: a.courtier });
  }
  return cards;
}

/** Play without a target: a courtier into the outer circle, an event. */
export function untargeted(actions: Action[], card: number): Selection | null {
  const plain = actions.find((a) => a.card === card && a.kind === "play" && a.courtier === null && a.target_player === null);
  return plain ? { card, kind: "play", courtier: null, target_player: null } : null;
}

export function discarding(actions: Action[], card: number): Selection | null {
  return actions.some((a) => a.card === card && a.kind === "discard") ? { card, kind: "discard" } : null;
}

export function stage(actions: Action[], selection: Selection): Stage {
  const none = { offers: [], cards: new Map(), seats: new Map(), players: new Map() };

  if (isEmpty(selection)) {
    return { ...none, step: "start", active: null, cards: pickUps(actions) };
  }

  if (onlyCard(selection)) {
    const card = selection.card as number;
    const offers: Offer[] = [];
    const play = untargeted(actions, card);
    if (play) offers.push({ label: "Play", selection: play });
    const discard = discarding(actions, card);
    if (discard) offers.push({ label: "Discard & Draw", selection: discard });

    // Another card in hand swaps the pick-up; this one puts it down.
    const cards = pickUps(actions);
    for (const [uid, sel] of [...cards]) if (sel.kind === "move") cards.delete(uid);
    cards.set(card, PUT_DOWN);
    const players = new Map<number, Selection>();
    for (const a of actions) {
      if (a.card !== card || a.kind !== "play") continue;
      if (a.courtier !== null) cards.set(a.courtier, { card, kind: "play", courtier: a.courtier });
      if (a.target_player !== null) players.set(a.target_player, { card, kind: "play", target_player: a.target_player });
    }
    return { ...none, step: "card", active: card, offers, cards, players };
  }

  if (isMover(selection)) {
    const mover = selection.courtier as number;
    const seats = new Map<string, Selection>();
    for (const a of actions) {
      if (a.kind === "move" && a.courtier === mover && a.seat) seats.set(a.seat, { ...selection, seat: a.seat });
    }
    return { ...none, step: "mover", active: mover, cards: new Map([[mover, PUT_DOWN]]), seats };
  }

  // Part-way through an action: light whatever it still needs.
  const b = build(actions, selection);
  const active = typeof selection.card === "number" ? selection.card : (selection.courtier as number | null) ?? null;
  const cards = new Map<number, Selection>();
  if (active !== null) cards.set(active, PUT_DOWN);
  const seats = new Map<string, Selection>();
  const players = new Map<number, Selection>();
  const offers: Offer[] = [];
  const field = b.field;
  for (const value of b.choices) {
    const next = { ...selection, [field!]: value };
    if (field === "courtier" || field === "sacrifice") cards.set(value as number, next);
    else if (field === "seat") seats.set(value as string, next);
    else if (field === "target_player") players.set(value as number, next);
    else offers.push({ label: String(value), selection: next });
  }
  const step: Step = field === null ? "done" : field === "card" || field === "kind" ? "value" : field;
  return { step, active, offers, cards, seats, players };
}

/** Where a dragged card may land, and what landing there selects. */
export type DropKey = string; // "outer" | "discard" | "courtier:12" | "seat:Oracle" | "player:2"

export function drops(actions: Action[], dragged: number): Map<DropKey, Selection> {
  const out = new Map<DropKey, Selection>();
  const play = untargeted(actions, dragged);
  if (play) out.set("outer", play);
  const discard = discarding(actions, dragged);
  if (discard) out.set("discard", discard);
  for (const a of actions) {
    if (a.card === dragged && a.kind === "play") {
      if (a.courtier !== null) out.set(`courtier:${a.courtier}`, { card: dragged, kind: "play", courtier: a.courtier });
      if (a.target_player !== null) out.set(`player:${a.target_player}`, { card: dragged, kind: "play", target_player: a.target_player });
    }
    // An outer courtier dragged to a seat: a free move.
    if (a.card === null && a.kind === "move" && a.courtier === dragged && a.seat) {
      out.set(`seat:${a.seat}`, { card: null, kind: "move", courtier: dragged, seat: a.seat });
    }
  }
  return out;
}

/** The action a selection pins down, if it pins one down. */
export function settled(actions: Action[], selection: Selection): Action | null {
  if (isEmpty(selection)) return null;
  return build(actions, selection).chosen;
}
