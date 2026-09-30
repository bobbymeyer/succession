// The instruction line under the question: what to do next, in words.

import type { PickPrompt } from "./flow";
import type { Stage } from "./play";
import type { Card, View } from "./protocol";

/** Where the player is in building a move. */
export function hintFor(s: Stage, view: View, cards: Map<number, Card>): string {
  const name = (uid: number | null) => (uid !== null ? cards.get(uid)?.name ?? "it" : "it");
  switch (s.step) {
    case "start":
      return "Your move. Click a card to pick it up, or drag it where it goes.";
    case "card": {
      const aims = [...s.cards.values()].some((sel) => sel.courtier !== undefined && sel.courtier !== null) || s.players.size > 0;
      return aims
        ? `${name(s.active)}: click a lit ${s.players.size ? "player" : "courtier"} or drag the card onto one${s.offers.length ? ", or choose above it" : ""}. Click it again to put it down.`
        : `${name(s.active)}: choose above the card, or drag it to the outer circle or the discard pile. Click it again to put it down.`;
    }
    case "mover":
      return `${name(s.active)}: click a lit seat, or drag them into it.`;
    case "courtier":
      return "Click the courtier it targets.";
    case "seat":
      return "Click the seat it takes.";
    case "target_player":
      return "Click the player it targets.";
    default:
      return view.over ? "" : "Choose above the card.";
  }
}

/** A choice an event forced, or your discard down to the hand limit. */
export function pickHint(pick: PickPrompt): string {
  if (pick.card === null) {
    const more = pick.over === 1 ? "one more card" : `${pick.over} more cards`;
    return `Your hand is over the limit of 7. Discard ${more} to end your turn: click a lit card, or drag it to the discard pile.`;
  }
  return `${pick.card.name}: ${
    pick.kind === "courtier"
      ? "every player names a courtier to die, all at once. Click one of the lit courtiers."
      : "every player discards, all at once. Click a lit card, or drag it to the discard pile."
  }`;
}

/** The same instruction for a finger rather than a mouse. */
export const tapped = (hint: string) =>
  hint
    .replace(/,? or drag [^,.]*/g, "")
    .replace(/choose above (it|the card)/g, "choose below")
    .replace(/Choose above the card/g, "Choose below")
    .replace(/ Click it again to put it down\./g, "")
    .replace("Click a card to pick it up.", "Tap a card to pick it up, or hold one to read it.")
    .replace(/\bClick\b/g, "Tap")
    .replace(/\bclick\b/g, "tap");
