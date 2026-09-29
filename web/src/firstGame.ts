// A new player's first game is dealt kindly rather than at random: the deal
// named "first_game" in succession/deal.py, where you move first holding
// House Rising: Mitreas with two Mitreas courtiers in hand. The rest of the
// table is shuffled as usual. tests/test_deal.py keeps it kind.

export const FIRST_GAME_DEAL = "first_game";

/** The table the deal was written for: you and one of each bot, in this order. */
export const FIRST_GAME_TABLE = ["naive", "greedy", "strategic"];

/** Whether a deal should be the first game: nothing finished in this browser yet, the default table, no seed typed. */
export function isFirstGame(typed: number | undefined, finished: number | null, bots: string[]): boolean {
  return typed === undefined && finished === 0 && bots.join() === FIRST_GAME_TABLE.join();
}

/**
 * A deal given in the address, `?deal=<JSON>` (succession/deal.py's shape),
 * for the next game Play deals: how the browser tests set up a situation,
 * and a way to share one. Null when there is none, or it doesn't parse.
 */
export function urlDeal(): Record<string, unknown> | null {
  try {
    const text = new URLSearchParams(window.location.search).get("deal");
    const deal = text ? JSON.parse(text) : null;
    return deal && typeof deal === "object" ? deal : null;
  } catch {
    return null;
  }
}
