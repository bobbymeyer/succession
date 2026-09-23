import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Engine } from "./engine";
import { loadArt, NO_ART, preload, UiContext, type Art, type Ui } from "./art";
import { EMPTY, measure, play, type Snapshot } from "./flip";
import { FADE, HOLD, showHand } from "./hand";
import { clearGames, download, saveGame, savedGames } from "./history";
import { type Selection } from "./moves";
import { drops, settled, stage, type Stage } from "./play";
import type { Action, Card, GameRecord, GameRequest, TableOptions, Update, View } from "./protocol";
import { playerName, readableLog, seatColour, visibleCards } from "./names";
import { AgendaTracker } from "./components/AgendaTracker";
import { Board, NO_INTERACTION, type Interaction } from "./components/Board";
import { Credit } from "./components/Credit";
import { GameOver, winningCourt } from "./components/GameOver";
import { FrameControls } from "./components/Frame";
import { CardDetail, Inspect } from "./components/Inspect";
import { DiscardPile, StatusPanel } from "./components/Status";
import { Setup } from "./components/Setup";

// The pause after each bot move. Long enough to watch the card leave the
// bot's hand and land; Instant plays straight through.
const SPEEDS = { Slow: 2200, Normal: 1300, Fast: 550, Instant: 0 } as const;
type Speed = keyof typeof SPEEDS;

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

/** A card being dragged, from pointer-down until it is dropped. */
interface Drag {
  uid: number;
  source: HTMLElement;
  x0: number;
  y0: number;
  ghost: HTMLElement | null;
  targets: Map<string, () => void>;
}

/** The instruction line for where the player is in building a move. */
function hintFor(s: Stage, view: View, cards: Map<number, Card>): string {
  const name = (uid: number | null) => (uid !== null ? cards.get(uid)?.name ?? "it" : "it");
  switch (s.step) {
    case "start":
      return "Your move. Click a card to pick it up, or drag it where it goes.";
    case "card": {
      const aims = [...s.cards.values()].some((sel) => sel.courtier !== undefined && sel.courtier !== null) || s.players.size > 0;
      return aims
        ? `${name(s.active)}: click a lit ${s.players.size ? "player" : "courtier"} or drag the card onto one${s.offers.length ? ", or choose above it" : ""}. Click it again to put it down.`
        : `${name(s.active)}: choose above the card, or drag it to the outer circle or the discard pile. Click it again to put it down.`;
    }
    case "mover":
      return `${name(s.active)}: click a lit seat, or drag them into it.`;
    case "courtier":
      return "Click the courtier it targets.";
    case "seat":
      return "Click the seat it takes.";
    case "sacrifice":
      return "Click a courtier in your hand to pay for it.";
    case "target_player":
      return "Click the player it targets.";
    default:
      return view.over ? "" : "Choose above the card.";
  }
}

export function App() {
  const engine = useMemo(() => new Engine(), []);
  const [options, setOptions] = useState<TableOptions | null>(null);
  const [fatal, setFatal] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [shown, setShown] = useState<Update | null>(null);
  const [log, setLog] = useState<{ text: string; view: Update["view"] }[]>([]);
  const [pending, setPending] = useState(0); // updates still to play out
  const [busy, setBusy] = useState(false);
  const [speed, setSpeed] = useState<Speed>(savedSpeed);

  const [selection, setSelection] = useState<Selection>({});
  const [picked, setPicked] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const [tab, setTab] = useState<"agenda" | "log">("agenda");
  const [dropping, setDropping] = useState<Set<string>>(() => new Set());
  const dragging = useRef<Drag | null>(null);
  const justDragged = useRef(false);

  // Escape puts down whatever is picked up.
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelection({});
        setPicked(null);
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  const [saved, setSaved] = useState<number | null>(() => savedGames().length);

  const [art, setArt] = useState<Art>(NO_ART);
  const [inspecting, setInspecting] = useState<Card | null>(null);
  const [hovered, setHovered] = useState<Card | null>(null);
  const ui = useMemo<Ui>(() => ({ art, inspect: setInspecting, hover: setHovered }), [art]);

  useEffect(() => {
    engine.ready.then((r) => setOptions(r.options)).catch((e: Error) => setFatal(e.message));
    // Without pictures the game still plays, drawn as type.
    loadArt().then(setArt, () => setArt(NO_ART));
  }, [engine]);

  // Bot turns arrive all at once; show them one at a time.
  const queue = useRef<Update[]>([]);
  const timer = useRef<number | null>(null);
  const speedRef = useRef(speed);
  speedRef.current = speed;
  // Where every card was just before the update now being drawn.
  const before = useRef<{ snapshot: Snapshot; actor: number; action: Action | null } | null>(null);
  const fresh = useRef(false);
  // The bot whose card is still crossing the table keeps the spotlight until
  // it lands; after that it passes to whoever is thinking next.
  const [playing, setPlaying] = useState<number | null>(null);
  const playingTimer = useRef<number | null>(null);

  const pump = useCallback(() => {
    timer.current = null;
    const next = queue.current.shift();
    if (!next) return;
    before.current = { snapshot: fresh.current ? EMPTY : measure(), actor: next.actor, action: next.action };
    fresh.current = false;
    setShown(next);
    setLog((l) => [...l, ...next.log.map((text) => ({ text, view: next.view }))]);
    setPending(queue.current.length);
    if (queue.current.length) {
      const delay = next.prompt ? 0 : SPEEDS[speedRef.current];
      timer.current = window.setTimeout(pump, delay);
    }
  }, []);

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
      showHand(from.actor, from.action, seatColour(from.actor), duration);
    }
    play(from.snapshot, from.actor, shown.view.you, duration);
  }, [shown]);

  // A finished game is kept for export once the last bot move has played out.
  const result = shown?.result ?? null;
  useEffect(() => {
    if (!result || pending > 0) return;
    setSaved(saveGame(result.record) ? savedGames().length : null);
  }, [result, pending]);

  const send = useCallback(
    async (request: GameRequest, restart = false) => {
      if (restart) preload(art);
      setBusy(true);
      setError(null);
      try {
        const updates = await engine.send(request);
        if (restart) {
          if (timer.current !== null) window.clearTimeout(timer.current);
          timer.current = null;
          queue.current = [];
          fresh.current = true;
          setLog([]);
        }
        queue.current.push(...updates);
        setPending(queue.current.length);
        if (timer.current === null) pump();
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(false);
        setSelection({});
        setPicked(null);
        setCopied(false);
      }
    },
    [engine, pump, art],
  );

  const exportCsv = useCallback(async () => {
    try {
      download("succession-games.csv", await engine.exportCsv(savedGames()), "text/csv");
    } catch (e) {
      setError((e as Error).message);
    }
  }, [engine]);

  const changeSpeed = (s: Speed) => {
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
  };

  const toSetup = () => {
    setShown(null);
  };

  if (fatal) {
    return (
      <main className="app">
        <p className="error">The game engine didn't start: {fatal}</p>
      </main>
    );
  }
  if (!options) {
    return (
      <main className="app">
        <p className="loading">Loading the game engine…</p>
      </main>
    );
  }
  if (!shown) {
    return (
      <UiContext.Provider value={ui}>
        <main className="app">
          <Setup
            options={options}
            saved={saved}
            onDeal={(players, seed) => send({ type: "new", players, seed }, true)}
            onLoad={(record: GameRecord) => send({ type: "load", record }, true)}
            onExport={exportCsv}
            onClear={() => {
              clearGames();
              setSaved(savedGames().length);
            }}
          />
          {error && <p className="error">{error}</p>}
          <Credit />
        </main>
      </UiContext.Provider>
    );
  }

  const { view, prompt } = shown;
  const waiting = pending > 0 || busy;
  const cards = visibleCards(view);
  const turnPrompt = !waiting && prompt?.kind === "turn" ? prompt : null;
  const pickPrompt = !waiting && prompt && prompt.kind !== "turn" ? prompt : null;
  const latest = log.length ? readableLog(log[log.length - 1].view, log[log.length - 1].text) : null;

  // -- playing by hand: click to pick up, or drag -----------------------------
  const actions = turnPrompt?.options ?? [];
  const now: Stage | null = turnPrompt ? stage(actions, selection) : null;
  const answer = (action: Action) => send({ type: "answer", choice: action.index });
  /** Take a selection: play it if it pins one move down, else wait for more. */
  const apply = (next: Selection) => {
    const action = settled(actions, next);
    if (action) answer(action);
    else setSelection(next);
  };
  const pick = (uid: number) => send({ type: "answer", choice: uid });
  const pickVerb = pickPrompt?.kind === "courtier" ? "Name to die" : "Discard";

  /** Where a card may be dragged, and what dropping it there does. */
  const targetsFor = (uid: number): Map<string, () => void> => {
    const out = new Map<string, () => void>();
    if (turnPrompt && (now?.active === null || now?.active === uid)) {
      for (const [key, sel] of drops(actions, uid)) out.set(key, () => apply(sel));
    } else if (pickPrompt?.kind === "discard" && pickPrompt.options.some((c) => c.uid === uid)) {
      out.set("discard", () => pick(uid));
    }
    return out;
  };

  const press = (uid: number, e: React.PointerEvent<HTMLElement>) => {
    if (e.button !== 0) return;
    const targets = targetsFor(uid);
    if (!targets.size) return;
    const source = (e.currentTarget.closest(".card") as HTMLElement) ?? e.currentTarget;
    dragging.current = { uid, source, x0: e.clientX, y0: e.clientY, ghost: null, targets };
    const move = (ev: PointerEvent) => {
      const d = dragging.current;
      if (!d) return;
      if (!d.ghost) {
        if (Math.hypot(ev.clientX - d.x0, ev.clientY - d.y0) < 6) return; // still a click
        const rect = d.source.getBoundingClientRect();
        const ghost = d.source.cloneNode(true) as HTMLElement;
        ghost.classList.add("ghost");
        ghost.style.width = `${rect.width}px`;
        ghost.style.left = `${rect.left}px`;
        ghost.style.top = `${rect.top}px`;
        ghost.dataset.dx = String(d.x0 - rect.left);
        ghost.dataset.dy = String(d.y0 - rect.top);
        ghost.removeAttribute("data-uid");
        document.body.appendChild(ghost);
        d.ghost = ghost;
        d.source.classList.add("dragging");
        setDropping(new Set(d.targets.keys()));
      }
      d.ghost.style.left = `${ev.clientX - Number(d.ghost.dataset.dx)}px`;
      d.ghost.style.top = `${ev.clientY - Number(d.ghost.dataset.dy)}px`;
    };
    const up = (ev: PointerEvent) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
      const d = dragging.current;
      dragging.current = null;
      if (!d?.ghost) return; // a click: the button's own click handler takes it
      d.ghost.remove();
      d.source.classList.remove("dragging");
      setDropping(new Set());
      justDragged.current = true;
      setTimeout(() => (justDragged.current = false), 0);
      const key = document.elementFromPoint(ev.clientX, ev.clientY)?.closest("[data-drop]")?.getAttribute("data-drop");
      if (key) d.targets.get(key)?.();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
  };

  const offerButtons = (offers: { label: string; run(): void }[]) => (
    <div className="offers" role="group" aria-label="Choose">
      {offers.map((o) => (
        <button key={o.label} type="button" className="offer" data-testid="offer" onClick={o.run}>
          {o.label}
        </button>
      ))}
    </div>
  );

  let act: Interaction = NO_INTERACTION;
  if (turnPrompt && now) {
    act = {
      cardLive: (uid) => now.cards.has(uid),
      cardSelected: (uid) => now.active === uid || selection.sacrifice === uid,
      onCard: (uid) => {
        if (justDragged.current) return;
        const next = now.cards.get(uid);
        if (next) apply(next);
      },
      seatLive: (seat) => now.seats.has(seat),
      seatSelected: (seat) => selection.seat === seat,
      onSeat: (seat) => {
        const next = now.seats.get(seat);
        if (next) apply(next);
      },
      playerLive: (p) => now.players.has(p),
      onPlayer: (p) => {
        const next = now.players.get(p);
        if (next) apply(next);
      },
      canDrag: (uid) => (now.active === null || now.active === uid) && drops(actions, uid).size > 0,
      onPress: press,
      dropLive: (key) => dropping.has(key),
      popover: (uid) =>
        uid === now.active && now.offers.length
          ? offerButtons(now.offers.map((o) => ({ label: o.label, run: () => apply(o.selection) })))
          : null,
    };
  } else if (pickPrompt) {
    const uids = pickPrompt.options.map((c) => c.uid);
    act = {
      ...NO_INTERACTION,
      cardLive: (uid) => uids.includes(uid),
      cardSelected: (uid) => picked === uid,
      onCard: (uid) => !justDragged.current && setPicked(picked === uid ? null : uid),
      canDrag: (uid) => pickPrompt.kind === "discard" && uids.includes(uid),
      onPress: press,
      dropLive: (key) => dropping.has(key),
      popover: (uid) => (uid === picked ? offerButtons([{ label: pickVerb, run: () => pick(uid) }]) : null),
    };
  }

  const hint = now
    ? hintFor(now, view, cards)
    : pickPrompt
      ? `${pickPrompt.card.name}: ${
          pickPrompt.kind === "courtier"
            ? "every player names a courtier to die. Click one of the lit courtiers."
            : "every player discards. Click a lit card, or drag it to the discard pile."
        }`
      : "";
  const pass = turnPrompt?.options.find((a) => a.kind === "pass") ?? null;

  const copyRecord = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(result.record));
      setCopied(true);
    } catch {
      setError("Couldn't copy to the clipboard.");
    }
  };
  // The same table again, freshly dealt.
  const playAgain = () => {
    if (!result) return;
    send({ type: "new", players: result.record.config.players as string[] }, true);
  };

  // Your agenda and the log share one slot under the question, a tab each.
  const myAgenda = view.you >= 0 ? view.players[view.you].agenda : null;
  const showing = myAgenda ? tab : "log";
  const tabs = (
    <section className="tabbed" aria-label="Agenda and log">
      <div className="tabs" role="tablist">
        {myAgenda && (
          <button
            type="button"
            role="tab"
            id="tab-agenda"
            aria-selected={showing === "agenda"}
            aria-controls="tabpanel"
            onClick={() => setTab("agenda")}
          >
            Agenda{" "}
            <small className={myAgenda.met ? "met" : ""}>
              {myAgenda.status.filter((c) => c.met).length}/{myAgenda.status.length}
            </small>
          </button>
        )}
        <button
          type="button"
          role="tab"
          id="tab-log"
          aria-selected={showing === "log"}
          aria-controls="tabpanel"
          onClick={() => setTab("log")}
        >
          Log
        </button>
      </div>
      <div className="tabpanel" id="tabpanel" role="tabpanel" aria-labelledby={`tab-${showing}`}>
        {showing === "agenda" && myAgenda ? (
          <AgendaTracker agenda={myAgenda} />
        ) : (
          <ol className="log" reversed aria-label="Game log">
            {log
              .slice()
              .reverse()
              .map((line, i) => (
                <li key={log.length - i}>{readableLog(line.view, line.text)}</li>
              ))}
          </ol>
        )}
      </div>
    </section>
  );

  return (
    <UiContext.Provider value={ui}>
      <main className="app game">
        <Board view={view} act={act} playing={playing} won={result && !waiting ? winningCourt(view) : undefined} />
        <div className="rail">
          <aside className="side">
            <div className="controls">
              <label>
                Bot speed{" "}
                <select aria-label="Bot speed" value={speed} onChange={(e) => changeSpeed(e.target.value as Speed)}>
                  {Object.keys(SPEEDS).map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
              <button type="button" onClick={toSetup}>
                New game
              </button>
            </div>
            <div className="controls frame">
              <FrameControls />
            </div>

            {result && !waiting ? (
              <GameOver
                view={view}
                result={result}
                saved={saved}
                copied={copied}
                onPlayAgain={playAgain}
                onNewTable={toSetup}
                onCopy={copyRecord}
                onDownloadRecord={() =>
                  download(`succession-game-${result.record.seed}.json`, JSON.stringify(result.record, null, 1), "application/json")
                }
                onExport={exportCsv}
              />
            ) : turnPrompt || pickPrompt ? (
              <StatusPanel hint={hint} prompt={turnPrompt ?? pickPrompt} onAction={answer} onPick={pick} pass={pass} />
            ) : (
              <div className="prompt" aria-live="polite">
                {latest && <p className="latest">{latest}</p>}
                <p className="thinking">{playerName(view, view.current)} to play…</p>
              </div>
            )}
            <DiscardPile view={view} dropLive={dropping.has("discard")} />
            {error && <p className="error">{error}</p>}
            {hovered && (
              <div className="preview" aria-hidden="true">
                <CardDetail card={hovered} />
              </div>
            )}
          </aside>
          {tabs}
        </div>
        <Credit />
        <Inspect card={inspecting} onClose={() => setInspecting(null)} />
      </main>
    </UiContext.Provider>
  );
}
