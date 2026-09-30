// What is laid over the table: the briefing, an event and its announcement,
// the hand-limit notice, the fall into chaos, the inspector and the rules.

import { useState } from "react";
import type { Card, TableOptions } from "../protocol";
import type { GameFlow } from "../useGameFlow";
import type { Play } from "../usePlay";
import { Briefing } from "./Briefing";
import { Chaos } from "./Chaos";
import { EventAnnouncement, EventBanner, EventModal, HandLimitNotice } from "./EventModal";
import { Inspect } from "./Inspect";
import { Rules } from "./Rules";

export function Overlays({
  flow,
  play,
  options,
  rulesOpen,
  onCloseRules,
  inspecting,
  onInspect,
}: {
  flow: GameFlow;
  play: Play;
  options: TableOptions;
  rulesOpen: boolean;
  onCloseRules(): void;
  inspecting: Card | null;
  onInspect(card: Card | null): void;
}) {
  // The game whose fall into chaos has been watched.
  const [chaosSeen, setChaosSeen] = useState<unknown>(null);
  const shown = flow.shown!;
  const view = shown.view;
  const { over, announce, events } = flow;
  return (
    <>
      {over?.timeout && chaosSeen !== over && (
        <Chaos rounds={Math.ceil(over.turns / view.players.length)} onDone={() => setChaosSeen(over)} />
      )}
      <Inspect card={inspecting} hand={view.hand} moves={play.movesFor} onPick={onInspect} onClose={() => onInspect(null)} />
      {rulesOpen && <Rules options={options} onClose={onCloseRules} />}
      {flow.phase === "briefing" && <Briefing view={view} onBegin={flow.begin} />}
      {flow.liveEvent && <EventBanner prompt={flow.liveEvent} actor={shown.actor} view={view} yours={flow.pick !== null} />}
      {flow.limitNotice && <HandLimitNotice key={view.turn} hand={view.hand.length} over={flow.pick!.over} onDone={flow.noteLimit} />}
      {announce?.prompt && (announce.prompt.kind === "courtier" || announce.prompt.kind === "discard") && (
        <EventAnnouncement
          key={flow.announceKey}
          prompt={announce.prompt}
          actor={announce.actor}
          view={announce.view}
          onDone={flow.endAnnounce}
        />
      )}
      {flow.event && events && (
        <EventModal
          key={`${flow.event.card.uid}:${events.update.view.turn}:${events.left}`}
          report={flow.event}
          view={events.update.view}
          onContinue={flow.carryOn}
        />
      )}
    </>
  );
}
