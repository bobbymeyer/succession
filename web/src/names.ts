import type { Card, View } from "./protocol";

const TIER_NAMES: Record<string, string> = {
  human: "Human",
  naive: "Naive bot",
  greedy: "Greedy bot",
  strategic: "Strategic bot",
};

export function tierName(tier: string): string {
  return TIER_NAMES[tier] ?? tier;
}

/** "You", or "P2 Greedy bot". */
export function playerName(view: View, seat: number): string {
  if (seat === view.you) return "You";
  return `P${seat} ${tierName(view.players[seat].tier)}`;
}

/** The engine's log says "P2"; the page says who that is. */
export function readableLog(view: View, line: string): string {
  return line
    .replace(/^\[t\d+\]\s*/, "")
    // The engine logs every seat as "P2 play ..."; "You play", "P2 plays".
    .replace(/^P(\d+) play /, (_, n: string) => (Number(n) === view.you ? `P${n} play ` : `P${n} plays `))
    .replace(/\bP(\d+)\b/g, (_, n: string) => (Number(n) < view.players.length ? playerName(view, Number(n)) : `P${n}`));
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
