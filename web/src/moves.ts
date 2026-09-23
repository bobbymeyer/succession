// Building a move by clicking, without the page knowing a single rule.
//
// The engine hands over every legal action, fully specified. A move is picked
// by narrowing that list one field at a time: click a card in hand and only
// the actions that play or discard it remain; click a courtier and only those
// aimed at them remain; and so on until one action is left to confirm. The
// board lights up exactly the things that would narrow the list further.

import type { Action } from "./protocol";

export const FIELDS = ["card", "kind", "courtier", "seat", "target_player", "sacrifice", "value"] as const;
export type Field = (typeof FIELDS)[number];
export type Value = Action[Field];
export type Selection = Partial<Record<Field, Value>>;

export function matching(actions: Action[], selection: Selection): Action[] {
  return actions.filter((a) => FIELDS.every((f) => !(f in selection) || a[f] === selection[f]));
}

function distinct(actions: Action[], field: Field): Value[] {
  return [...new Set(actions.map((a) => a[field]))];
}

/** The first field the remaining actions still disagree on. */
export function nextField(actions: Action[], selection: Selection): Field | null {
  return FIELDS.find((f) => !(f in selection) && distinct(actions, f).length > 1) ?? null;
}

export interface Builder {
  selection: Selection;
  remaining: Action[];
  /** What the player is choosing now; null when one action is left. */
  field: Field | null;
  /** The values that would narrow the choice, for `field`. */
  choices: Value[];
  /** The one action left, once the choice is made. */
  chosen: Action | null;
}

export function build(actions: Action[], selection: Selection): Builder {
  const remaining = matching(actions, selection);
  const field = nextField(remaining, selection);
  return {
    selection,
    remaining,
    field,
    choices: field ? distinct(remaining, field) : [],
    // Identical duplicates are possible; any of them will do.
    chosen: field === null && remaining.length > 0 ? remaining[0] : null,
  };
}

/** Choosing a value for the current field. */
export function choose(builder: Builder, value: Value): Selection {
  if (!builder.field) return builder.selection;
  return { ...builder.selection, [builder.field]: value };
}

/**
 * The selection a click on a card leads to, or null if the click means
 * nothing right now. Hand cards pick the card to play (or the courtier to
 * sacrifice); courtiers on the board pick a target -- or, with nothing yet
 * chosen, the courtier to move into an empty seat.
 */
export function clickCard(actions: Action[], builder: Builder, uid: number): Selection | null {
  const { field, choices, selection } = builder;
  if (field && (field === "card" || field === "courtier" || field === "sacrifice") && choices.includes(uid)) {
    return choose(builder, uid);
  }
  if (Object.keys(selection).length === 0 && actions.some((a) => a.kind === "move" && a.courtier === uid)) {
    return { card: null, kind: "move", courtier: uid };
  }
  return null;
}

export function cardIsLive(actions: Action[], builder: Builder, uid: number): boolean {
  return clickCard(actions, builder, uid) !== null;
}

export function seatIsLive(builder: Builder, seat: string): boolean {
  return builder.field === "seat" && builder.choices.includes(seat);
}
