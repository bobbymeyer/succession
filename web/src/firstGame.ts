// A new player's first game is dealt from one kind seed rather than a random
// one: you move first, holding House Rising: Argaian with two Argaian
// courtiers in hand. tools/friendly_seed.py found it; with a bot in your
// chair the naive, greedy and strategic bots all win from it, and a player
// choosing at random wins 7 games in 30 (about one in fifteen on a random
// deal). tests/test_friendly_seed.py keeps the engine from quietly changing it.

export const FIRST_GAME_SEED = 2791;

/** The table the seed was chosen for: you and one of each bot, in this order. */
export const FIRST_GAME_TABLE = ["naive", "greedy", "strategic"];

/**
 * The seed for a deal: the one typed in, else the kind one for a first game
 * (nothing finished in this browser yet, at the default table), else random.
 */
export function dealSeed(typed: number | undefined, finished: number | null, bots: string[]): number | undefined {
  if (typed !== undefined) return typed;
  const firstGame = finished === 0 && bots.join() === FIRST_GAME_TABLE.join();
  return firstGame ? FIRST_GAME_SEED : undefined;
}
