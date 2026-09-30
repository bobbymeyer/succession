// The conversation with the engine, paced for people to watch.
//
// A request comes back as a batch of updates (every bot move up to your next
// decision); they are shown one at a time, each card gliding from where it
// was. A new deal stops at the table as dealt until you begin, and each event
// stops play until it has been read. `flowOf` (flow.ts) turns this state into
// what the table is waiting on.

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { preload, type Art } from "./art";
import type { Engine } from "./engine";
import { flowOf, type EventQueue, type Flow } from "./flow";
import { EMPTY, measure, play, type Snapshot } from "./flip";
import { captionFor, FADE, HOLD, showHand } from "./hand";
import { saveGame, savedGames } from "./history";
import { seatColour, visibleCards } from "./names";
import type { Action, GameRequest, Update } from "./protocol";

// The pause after each bot move. Long enough to watch the card leave the
// bot's hand and land; Instant plays straight through.
export const SPEEDS = { Slow: 2200, Normal: 1300, Fast: 550, Instant: 0 } as const;
export type Speed = keyof typeof SPEEDS;

function savedSpeed(): Speed {
  try {
    const s = localStorage.getItem("succession.speed");
    if (s && s in SPEEDS) return s as Speed;
  } catch {
    // storage can be unavailable (private windows, sandboxed iframes)
  }
  return "Normal";
}

/** How long a card takes to cross the table: most of the pause between moves. */
function glide(speed: Speed): number {
  return Math.min(900, SPEEDS[speed] * 0.7);
}

export interface LogLine {
  text: string;
  view: Update["view"];
}

export interface GameFlow extends Flow {
  /** The update on screen; null at the title screen. */
  shown: Update | null;
  log: LogLine[];
  error: string | null;
  setError(message: string | null): void;
  /** Finished games kept in this browser; null when saving failed. */
  saved: number | null;
  refreshSaved(): void;
  speed: Speed;
  changeSpeed(speed: Speed): void;
  /** The bot whose card is still crossing the table. */
  playing: number | null;
  /** Send a request; `restart` for one that deals a new game. */
  send(request: GameRequest, restart?: boolean): Promise<void>;
  /** Close the briefing and let the bots move. */
  begin(): void;
  /** The event on screen has been read. */
  carryOn(): void;
  /** You have been told your turn ends over the hand limit. */
  noteLimit(): void;
  /** The events being read, one after another (`event` is the one on screen). */
  events: EventQueue | null;
  /** An event that asks you something, being announced; cleared when it goes. */
  announce: Update | null;
  announceKey: string;
  endAnnounce(): void;
  /** Back to the title screen. */
  toSetup(): void;
}

export function useGameFlow(
  engine: Engine,
  art: Art,
  hooks: {
    /** A new game is being dealt. */
    onRestart(): void;
    /** A request has come back, or failed: whatever was picked up is put down. */
    onSettle(): void;
  },
): GameFlow {
  const [shown, setShown] = useState<Update | null>(null);
  const [log, setLog] = useState<LogLine[]>([]);
  const [pending, setPending] = useState(0); // updates still to play out
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [speed, setSpeed] = useState<Speed>(savedSpeed);
  const [saved, setSaved] = useState<number | null>(() => savedGames().length);
  const [briefing, setBriefing] = useState(false);
  // Each event stops play until it has been read, one after another.
  const [events, setEvents] = useState<EventQueue | null>(null);
  // An event that stops to ask you something is announced first, once.
  const [announce, setAnnounce] = useState<Update | null>(null);
  const announced = useRef("");
  const [limitNoted, setLimitNoted] = useState<number | null>(null);
  // The bot whose card is still crossing the table keeps the spotlight until
  // it lands; after that it passes to whoever is thinking next.
  const [playing, setPlaying] = useState<number | null>(null);
  const playingTimer = useRef<number | null>(null);

  const hooksRef = useRef(hooks);
  hooksRef.current = hooks;

  // Bot turns arrive all at once; show them one at a time.
  const queue = useRef<Update[]>([]);
  const timer = useRef<number | null>(null);
  const speedRef = useRef(speed);
  speedRef.current = speed;
  // Where every card was just before the update now being drawn.
  const before = useRef<{ snapshot: Snapshot; actor: number; action: Action | null } | null>(null);
  const fresh = useRef(false);
  // A new deal stops at the table as dealt until you have read your agenda.
  const hold = useRef(false);

  const pump = useCallback(() => {
    timer.current = null;
    const next = queue.current.shift();
    if (!next) return;
    before.current = { snapshot: fresh.current ? EMPTY : measure(), actor: next.actor, action: next.action };
    fresh.current = false;
    setShown(next);
    setLog((l) => [...l, ...next.log.map((text) => ({ text, view: next.view }))]);
    setPending(queue.current.length);
    if (hold.current) {
      hold.current = false;
      if (next.view.you >= 0 && next.view.players[next.view.you]?.agenda) {
        setBriefing(true);
        return; // the bots wait for Begin
      }
    }
    const asking = next.prompt && next.prompt.kind !== "turn" && next.prompt.kind !== "block" ? next.prompt : null;
    if (asking?.card) {
      const key = `${asking.card.uid}:${next.view.turn}`;
      if (announced.current !== key) {
        announced.current = key;
        setAnnounce(next);
      }
    }
    if (next.events.length) {
      setEvents({ update: next, left: next.events.length });
      return; // play goes on from Continue
    }
    if (queue.current.length) {
      const delay = next.prompt ? 0 : SPEEDS[speedRef.current];
      timer.current = window.setTimeout(pump, delay);
    }
  }, []);

  // Each update drawn: the cards glide from where they were, and a bot's
  // hand shows what it played.
  useLayoutEffect(() => {
    const from = before.current;
    before.current = null;
    if (!from || !shown) return;
    const duration = glide(speedRef.current);
    if (playingTimer.current !== null) window.clearTimeout(playingTimer.current);
    playingTimer.current = null;
    const bot = from.actor >= 0 && from.actor !== shown.view.you && duration > 0;
    setPlaying(bot ? from.actor : null);
    if (bot) playingTimer.current = window.setTimeout(() => setPlaying(null), duration + HOLD + FADE);
    // A bot's hand first, measured before the cards set off.
    if (from.action && from.actor >= 0 && from.actor !== shown.view.you && from.snapshot.cards.size) {
      const names = visibleCards(shown.view);
      const name = (uid: number | null) => (uid !== null ? names.get(uid)?.name ?? "" : "");
      showHand(from.actor, from.action, seatColour(from.actor), duration, captionFor(from.action, name));
    }
    play(from.snapshot, from.actor, shown.view.you, duration);
  }, [shown]);

  // A finished game is kept for export once the last bot move has played out.
  const result = shown?.result ?? null;
  useEffect(() => {
    if (!result || pending > 0) return;
    if (result.record.scenario) return; // the tutorial is not a game to keep
    setSaved(saveGame(result.record) ? savedGames().length : null);
  }, [result, pending]);

  const send = useCallback(
    async (request: GameRequest, restart = false) => {
      if (restart) {
        preload(art);
        hooksRef.current.onRestart();
      }
      setBusy(true);
      setError(null);
      try {
        const updates = await engine.send(request);
        if (restart) {
          if (timer.current !== null) window.clearTimeout(timer.current);
          timer.current = null;
          queue.current = [];
          fresh.current = true;
          hold.current = request.type === "new" || request.type === "tutorial";
          setBriefing(false);
          setEvents(null);
          setAnnounce(null);
          setLog([]);
        }
        queue.current.push(...updates);
        setPending(queue.current.length);
        if (timer.current === null) pump();
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(false);
        hooksRef.current.onSettle();
      }
    },
    [engine, pump, art],
  );

  const changeSpeed = useCallback(
    (s: Speed) => {
      setSpeed(s);
      try {
        localStorage.setItem("succession.speed", s);
      } catch {
        // not remembered; fine
      }
      // Instant should flush what is still queued.
      if (s === "Instant" && timer.current !== null) {
        window.clearTimeout(timer.current);
        pump();
      }
    },
    [pump],
  );

  const begin = useCallback(() => {
    setBriefing(false);
    if (timer.current === null) pump();
  }, [pump]);

  const carryOn = useCallback(() => {
    // The next event in this update, or back to play.
    if (events && events.left > 1) {
      setEvents({ ...events, left: events.left - 1 });
      return;
    }
    setEvents(null);
    if (timer.current === null && queue.current.length) timer.current = window.setTimeout(pump, 250);
  }, [pump, events]);

  const toSetup = useCallback(() => {
    setBriefing(false);
    setEvents(null);
    setAnnounce(null);
    setShown(null);
  }, []);

  const flow = flowOf({ shown, pending, busy, briefing, events, limitNoted });
  return {
    ...flow,
    shown,
    log,
    error,
    setError,
    saved,
    refreshSaved: () => setSaved(savedGames().length),
    speed,
    changeSpeed,
    playing,
    send,
    begin,
    carryOn,
    noteLimit: () => shown && setLimitNoted(shown.view.turn),
    events,
    announce,
    announceKey: announced.current,
    endAnnounce: () => setAnnounce(null),
    toSetup,
  };
}
