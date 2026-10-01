// Where playtest reports and bug reports go: the repository's issue forms
// (.github/ISSUE_TEMPLATE), opened with what the page already knows filled in.

import { playerName } from "./names";
import type { Result, View } from "./protocol";

const ISSUES = "https://github.com/bobbymeyer/succession/issues/new";
// GitHub refuses very long addresses; a record longer than this is pasted by hand.
const MAX_URL = 7000;

/** This build, as the footer and the reports name it. */
export function buildName(): string {
  return __BUILD__.date ? `${__BUILD__.commit} (${__BUILD__.date})` : __BUILD__.commit;
}

function issue(template: string, fields: Record<string, string>): string {
  const q = new URLSearchParams({ template, ...fields });
  return `${ISSUES}?${q}`;
}

/** A bug report, from anywhere in the game. */
export function bugReportUrl(): string {
  return issue("bug.yml", { build: buildName(), device: navigator.userAgent });
}

/**
 * A playtest report on a finished game: the table, your agenda, who won and
 * how long it took, and the game record when it fits in the address (when it
 * does not, `fits` is false and the page puts it on the clipboard instead).
 */
export function playtestReport(view: View, result: Result): { url: string; fits: boolean } {
  const players = (result.record.config.players as string[] | undefined) ?? [];
  const rounds = Math.ceil(result.turns / view.players.length);
  const fields: Record<string, string> = {
    build: buildName(),
    table: `${view.players.length} players: ${players.join(", ")}`,
    agenda: view.players[view.you]?.agenda?.name ?? "",
    result: result.timeout
      ? "No winner: the game ran out of rounds"
      : result.winners.map((w) => playerName(view, w)).join(" and "),
    length: `${result.turns} turns (${rounds} rounds)`,
  };
  const record = JSON.stringify(result.record);
  const full = issue("playtest.yml", { ...fields, record });
  if (full.length <= MAX_URL) return { url: full, fits: true };
  return { url: issue("playtest.yml", { ...fields, record: "(on your clipboard: paste it here)" }), fits: false };
}
