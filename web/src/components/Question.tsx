// The question the table is asking, where the rail (or the phone's dock)
// keeps it: the end of the game, a block, your move or a forced choice, or
// who is thinking.

import type { ReactNode } from "react";
import { tapped } from "../hints";
import { playerName, readableLog } from "../names";
import type { GameFlow } from "../useGameFlow";
import type { Play } from "../usePlay";
import { BlockPanel, StatusPanel } from "./Status";

export function Question({
  flow,
  play,
  phone,
  gameOver,
}: {
  flow: GameFlow;
  play: Play;
  phone: boolean;
  /** The end-of-game panel, drawn when the game is over. */
  gameOver: ReactNode;
}) {
  const view = flow.shown!.view;
  if (flow.phase === "over") return <>{gameOver}</>;
  if (flow.block) return <BlockPanel view={view} prompt={flow.block} onChoose={play.pick} />;
  if (flow.turn || flow.pick) {
    return (
      <StatusPanel
        hint={phone ? tapped(play.hint) : play.hint}
        prompt={flow.turn ?? flow.pick}
        onAction={play.answer}
        onPick={play.pick}
        pass={flow.turn?.options.find((a) => a.kind === "pass") ?? null}
        winning={play.winning}
      />
    );
  }
  const last = flow.log[flow.log.length - 1];
  const latest = last ? readableLog(last.view, last.text) : null;
  return (
    <div className="prompt" aria-live="polite">
      {latest && <p className="latest">{latest}</p>}
      <p className="thinking">{playerName(view, view.current)} to play…</p>
    </div>
  );
}
