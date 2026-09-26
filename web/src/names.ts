import type { Card, View } from "./protocol";

const TIER_NAMES: Record<string, string> = {
  human: "Human",
  naive: "Naive bot",
  greedy: "Greedy bot",
  strategic: "Strategic bot",
  tutor: "Rival",
};

export function tierName(tier: string): string {
  return TIER_NAMES[tier] ?? tier;
}

/** Each seat's colour: its chip, and its hand when it plays. Clear of the
 *  gold that marks your own choices and the red that marks a selection. */
const SEAT_COLOURS = ["#4fc3c7", "#b48ef0", "#6fcf7f", "#f29e5c", "#6fa8ff", "#f07fbf", "#d4d46a", "#9aa3b5"];

export function seatColour(seat: number): string {
  return SEAT_COLOURS[seat % SEAT_COLOURS.length];
}

/** "You", or "P2 Greedy bot". */
export function playerName(view: View, seat: number): string {
  if (seat === view.you) return "You";
  return `P${seat} ${tierName(view.players[seat].tier)}`;
}

/** The engine's log says "P2"; the page says who that is. */
export function readableLog(view: View, line: string): string {
  const you = `P${view.you}`;
  return (
    line
      .replace(/^\[t\d+\]\s*/, "")
      // The engine writes "P2 play ...", "P2 discards ... and draws": third
      // person for everyone. Put the verbs right for the seat that is "You".
      .replace(/^P(\d+) play /, (_, n: string) => (Number(n) === view.you ? `P${n} play ` : `P${n} plays `))
      .replace(new RegExp(`^${you} (discard|move|skip|name|draw)s\\b`), `${you} $1`)
      .replace(new RegExp(`^${you} has\\b`), `${you} have`)
      .replace(new RegExp(`^(${you} discard .*) and draws$`), "$1 and draw")
      .replace(new RegExp(`\\b${you}'s\\b`, "g"), "your")
      .replace(new RegExp(`^(${you} skip) their turn`), "$1 your turn")
      .replace(/\bP(\d+)\b/g, (_, n: string) => (Number(n) < view.players.length ? playerName(view, Number(n)) : `P${n}`))
  );
}

/** Every card the viewer can see, by uid. */
export function visibleCards(view: View): Map<number, Card> {
  const cards = new Map<number, Card>();
  const add = (card: Card | null | undefined) => {
    if (!card) return;
    cards.set(card.uid, card);
    add(card.defense);
  };
  view.hand.forEach(add);
  view.outer.forEach(add);
  view.seats.forEach((s) => add(s.courtier));
  add(view.discard_top);
  return cards;
}
