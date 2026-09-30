// What the table is waiting on, worked out in one place.
//
// A game on screen is always in one phase: dealt and waiting for you to read
// your agenda, stopped for an event, watching the bots, waiting on your turn,
// on a choice an event forced, on a block, or over. The prompts the page acts
// on, and the notices laid over the table, all follow from the phase and the
// update on screen -- nothing else decides them. `flowOf` is pure, so each
// rule here can be checked without a browser (tests/flow.spec.ts).

import type { EventReport, Prompt, Result, Update } from "./protocol";

export type TurnPrompt = Extract<Prompt, { kind: "turn" }>;
export type PickPrompt = Extract<Prompt, { kind: "courtier" | "discard" }>;
export type BlockPrompt = Extract<Prompt, { kind: "block" }>;

/** The events an update set off, being read one after another. */
export interface EventQueue {
  update: Update;
  /** How many of the update's events are still to be read, this one included. */
  left: number;
}

/** The state the flow is worked out from (useGameFlow holds it). */
export interface FlowInput {
  shown: Update | null;
  /** Updates still queued to play out. */
  pending: number;
  /** A request is with the engine. */
  busy: boolean;
  /** The table as dealt, waiting for you to read your agenda and begin. */
  briefing: boolean;
  events: EventQueue | null;
  /** The turn whose hand-limit discard you have been told about. */
  limitNoted: number | null;
}

export type Phase =
  | "setup" // no game: the title screen
  | "briefing" // dealt; the bots wait until you begin
  | "event" // an event's result is on screen; play goes on from Continue
  | "watching" // the bots are moving, or the engine is thinking
  | "turn" // your move
  | "pick" // a choice an event forced, or your hand-limit discard
  | "block" // a rival's attack you may block
  | "over";

export interface Flow {
  phase: Phase;
  /** Play has caught up with the engine and nothing is being read. */
  settled: boolean;
  turn: TurnPrompt | null;
  pick: PickPrompt | null;
  block: BlockPrompt | null;
  /** The event asking the table something, in effect until its result is shown. */
  liveEvent: PickPrompt | null;
  /** Your turn ended over the hand limit and you have not been told yet. */
  limitNotice: boolean;
  /** The event result to show now. */
  event: EventReport | null;
  /** The finished game, once its last move has played out. */
  over: Result | null;
}

export function flowOf({ shown, pending, busy, briefing, events, limitNoted }: FlowInput): Flow {
  const none: Flow = {
    phase: "setup",
    settled: true,
    turn: null,
    pick: null,
    block: null,
    liveEvent: null,
    limitNotice: false,
    event: null,
    over: null,
  };
  if (!shown) return none;

  const { prompt, result } = shown;
  // An event on screen holds any question behind it until it has been read.
  const settled = pending === 0 && !busy && events === null;
  const turn = settled && prompt?.kind === "turn" ? prompt : null;
  const pick = settled && prompt && (prompt.kind === "courtier" || prompt.kind === "discard") ? prompt : null;
  const block = settled && prompt?.kind === "block" ? prompt : null;
  const asking = prompt && (prompt.kind === "courtier" || prompt.kind === "discard") ? prompt : null;
  const event = events ? events.update.events[events.update.events.length - events.left] : null;
  const over = result && settled ? result : null;

  const phase: Phase = over
    ? "over"
    : briefing
      ? "briefing"
      : event
        ? "event"
        : turn
          ? "turn"
          : pick
            ? "pick"
            : block
              ? "block"
              : "watching";

  return {
    phase,
    settled,
    turn,
    pick,
    block,
    // Kept up while the others choose after you have, not only while it is yours.
    liveEvent: asking?.card && !events && !result ? asking : null,
    limitNotice: pick?.kind === "discard" && pick.card === null && limitNoted !== shown.view.turn && !events && !briefing,
    event,
    over,
  };
}
