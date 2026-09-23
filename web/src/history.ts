// Finished games, kept in this browser so a playtester can hand over a batch
// at once. Only the records are kept -- seed, rules and decisions -- and the
// engine replays them into log rows on export, so the rows always come from
// the simulator's own code.

import type { GameRecord } from "./protocol";

const KEY = "succession.games";
const LIMIT = 500;

export function savedGames(): GameRecord[] {
  try {
    const raw = localStorage.getItem(KEY);
    const games = raw ? (JSON.parse(raw) as GameRecord[]) : [];
    return Array.isArray(games) ? games : [];
  } catch {
    return []; // storage can be missing: private windows, sandboxed iframes
  }
}

/** Keep a finished game. Returns false if storage is unavailable. */
export function saveGame(record: GameRecord): boolean {
  try {
    const games = savedGames();
    const text = JSON.stringify(record);
    if (games.some((g) => JSON.stringify(g) === text)) return true; // a reloaded game
    games.push(record);
    localStorage.setItem(KEY, JSON.stringify(games.slice(-LIMIT)));
    return true;
  } catch {
    return false;
  }
}

export function clearGames() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // nothing kept, nothing to clear
  }
}

/** Hand the browser a file to save. */
export function download(name: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
