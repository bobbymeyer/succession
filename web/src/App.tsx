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
import { Board, Hand, marksFor, NO_INTERACTION, type Interaction } from "./components/Board";
import { usePhone } from "./usePhone";
import { warmOffline } from "./offline";
import { Credit } from "./components/Credit";
import { GameOver, winningCourt } from "./components/GameOver";
import { Briefing } from "./components/Briefing";
import { EventAnnouncement, EventModal } from "./components/EventModal";
import { Intro, introSeen } from "./components/Intro";
import { Chaos } from "./components/Chaos";
import { Rules } from "./components/Rules";
import { CoachPanel } from "./components/Coach";
import { FIRST_GAME_TABLE } from "./firstGame";
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

/** How long a finger holds a card before it can be dragged. */
const DRAG_HOLD_MS = 200;

/** The instruction for a finger rather than a mouse. */
const tapped = (hint: string) =>
  hint
    .replace(/,? or drag [^,.]*/g, "")
    .replace(/choose above (it|the card)/g, "choose below")
    .replace(/Choose above the card/g, "Choose below")
    .replace(/ Click it again to put it down\./g, "")
    .replace("Click a card to pick it up.", "Tap a card to pick it up, or hold one to read it.")
    .replace(/\bClick\b/g, "Tap")
    .replace(/\bclick\b/g, "tap");

type Sheet = "agenda" | "log" | "discard" | null;

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
  // The story plays on a first visit, over the engine's boot.
  const [intro, setIntro] = useState(() => !introSeen());
  const [rulesOpen, setRulesOpen] = useState(false);
  // On a phone: the menu, and the sheet pulled up from the dock.
  const phone = usePhone();
  const [menuOpen, setMenuOpen] = useState(false);
  const [sheet, setSheet] = useState<Sheet>(null);
  // The game whose fall into chaos has been watched.
  const [chaosSeen, setChaosSeen] = useState<Update["result"]>(null);
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

  // Once the engine and the art are in, the offline cache takes the rest.
  useEffect(() => {
    if (options && art !== NO_ART) warmOffline(art.offline);
  }, [options, art]);

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
  // A new deal stops at the table as dealt until you have read your agenda.
  const hold = useRef(false);
  const [briefing, setBriefing] = useState(false);
  // Each event stops play until it has been read, one after another.
  const [events, setEvents] = useState<{ update: Update; left: number } | null>(null);
  // An event that stops to ask you something is announced first, once.
  const [announce, setAnnounce] = useState<Update | null>(null);
  const announced = useRef("");
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
    if (hold.current) {
      hold.current = false;
      if (next.view.you >= 0 && next.view.players[next.view.you]?.agenda) {
        setBriefing(true);
        return; // the bots wait for Begin
      }
    }
    const asking = next.prompt && next.prompt.kind !== "turn" ? next.prompt : null;
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
    if (result.record.scenario) return; // the tutorial is not a game to keep
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

  const toSetup = () => {
    setBriefing(false);
    setEvents(null);
    setAnnounce(null);
    setShown(null);
  };

  if (intro) return <Intro onDone={() => setIntro(false)} />;
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
            onTutorial={() => send({ type: "tutorial" }, true)}
            onLoad={(record: GameRecord) => send({ type: "load", record }, true)}
            onExport={exportCsv}
            onClear={() => {
              clearGames();
              setSaved(savedGames().length);
            }}
            onIntro={() => setIntro(true)}
            onRules={() => setRulesOpen(true)}
          />
          {rulesOpen && <Rules options={options} onClose={() => setRulesOpen(false)} />}
          {error && <p className="error">{error}</p>}
          <Credit />
        </main>
      </UiContext.Provider>
    );
  }

  const { view, prompt } = shown;
  // An event on screen holds any question behind it until it has been read.
  const waiting = pending > 0 || busy || events !== null;
  const cards = visibleCards(view);
  const turnPrompt = !waiting && prompt?.kind === "turn" ? prompt : null;
  const pickPrompt = !waiting && prompt && prompt.kind !== "turn" ? prompt : null;
  const latest = log.length ? readableLog(log[log.length - 1].view, log[log.length - 1].text) : null;

  // -- playing by hand: click to pick up, or drag -----------------------------
  const actions = turnPrompt?.options ?? [];
  const now: Stage | null = turnPrompt ? stage(actions, selection) : null;
  const answer = (action: Action) => send({ type: "answer", choice: action.index });
  // Moves that win you the game now, and the cards in them, lit on the table.
  const winning = actions.filter((a) => a.wins);
  const marks = marksFor(
    view,
    new Set(winning.flatMap((a) => [a.card, a.courtier].filter((u): u is number => u !== null))),
  );
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
    // A finger has to hold a card a moment before it drags: until then a
    // swipe is the page scrolling, and the drag lets go. Once it is held, the
    // page stops scrolling under it.
    const touch = e.pointerType === "touch";
    let armed = !touch;
    const block = (tev: TouchEvent) => armed && tev.preventDefault();
    const arm = touch
      ? window.setTimeout(() => {
          armed = true;
          source.classList.add("armed");
          navigator.vibrate?.(8);
        }, DRAG_HOLD_MS)
      : 0;
    if (touch) document.addEventListener("touchmove", block, { passive: false });
    const release = () => {
      window.clearTimeout(arm);
      source.classList.remove("armed");
      document.removeEventListener("touchmove", block);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
    };
    const move = (ev: PointerEvent) => {
      const d = dragging.current;
      if (!d) return;
      if (!d.ghost) {
        if (Math.hypot(ev.clientX - d.x0, ev.clientY - d.y0) < 6) return; // still a click
        // Moved before the hold, or held into a look at the card: not a drag.
        if (!armed || document.querySelector("dialog[open]")) {
          release();
          dragging.current = null;
          return;
        }
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
      release();
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
      ? pickPrompt.card === null
        ? `Your hand is over the limit of 7. Discard ${pickPrompt.over === 1 ? "one more card" : `${pickPrompt.over} more cards`} to end your turn: click a lit card, or drag it to the discard pile.`
        : `${pickPrompt.card.name}: ${
            pickPrompt.kind === "courtier"
              ? "every player names a courtier to die, all at once. Click one of the lit courtiers."
              : "every player discards, all at once. Click a lit card, or drag it to the discard pile."
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
    // After the tutorial, a real game at the default table.
    const players = result.record.scenario ? ["human", ...FIRST_GAME_TABLE] : (result.record.config.players as string[]);
    send({ type: "new", players }, true);
  };

  // Your agenda and the log share one slot under the question, a tab each.
  const myAgenda = view.you >= 0 ? view.players[view.you].agenda : null;
  const showing = myAgenda ? tab : "log";
  const logList = (
    <ol className="log" reversed aria-label="Game log">
      {log
        .slice()
        .reverse()
        .map((line, i) => (
          <li key={log.length - i}>{readableLog(line.view, line.text)}</li>
        ))}
    </ol>
  );
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
          logList
        )}
      </div>
    </section>
  );

  const speedControl = (
    <label>
      Bot speed{" "}
      <select aria-label="Bot speed" value={speed} onChange={(e) => changeSpeed(e.target.value as Speed)}>
        {Object.keys(SPEEDS).map((s) => (
          <option key={s}>{s}</option>
        ))}
      </select>
    </label>
  );
  const question = (
    <>
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
        <StatusPanel
          hint={phone ? tapped(hint) : hint}
          prompt={turnPrompt ?? pickPrompt}
          onAction={answer}
          onPick={pick}
          pass={pass}
          winning={winning}
        />
      ) : (
        <div className="prompt" aria-live="polite">
          {latest && <p className="latest">{latest}</p>}
          <p className="thinking">{playerName(view, view.current)} to play…</p>
        </div>
      )}
    </>
  );
  const overlays = (
    <>
      {result?.timeout && !waiting && chaosSeen !== result && (
        <Chaos rounds={Math.ceil(result.turns / view.players.length)} onDone={() => setChaosSeen(result)} />
      )}
      <Inspect card={inspecting} onClose={() => setInspecting(null)} />
      {rulesOpen && options && <Rules options={options} onClose={() => setRulesOpen(false)} />}
      {briefing && <Briefing view={view} onBegin={begin} />}
      {announce?.prompt && announce.prompt.kind !== "turn" && (
        <EventAnnouncement
          key={announced.current}
          prompt={announce.prompt}
          actor={announce.actor}
          view={announce.view}
          onDone={() => setAnnounce(null)}
        />
      )}
      {events && (() => {
        const report = events.update.events[events.update.events.length - events.left];
        return (
          <EventModal
            key={`${report.card.uid}:${events.update.view.turn}:${events.left}`}
            report={report}
            view={events.update.view}
            onContinue={carryOn}
          />
        );
      })()}
    </>
  );

  // On a phone the table fits one screen: the board, with a menu in its
  // corner, over a dock that holds the question, your hand, and tabs that pull
  // up your agenda, the log and the discard pile.
  if (phone) {
    // A picked-up card's choices sit in the dock, not over the card, where
    // they would cover the question; with a way to put the card down.
    const offers =
      turnPrompt && now && now.active !== null && now.offers.length
        ? now.offers.map((o) => ({ label: o.label, run: () => apply(o.selection) }))
        : pickPrompt && picked !== null
          ? [{ label: pickVerb, run: () => pick(picked) }]
          : null;
    const holding = (turnPrompt && now?.active != null) || (pickPrompt && picked !== null);
    const putDown = () => {
      setSelection({});
      setPicked(null);
    };
    const phoneAct: Interaction = { ...act, popover: () => null };
    const met = myAgenda ? myAgenda.status.filter((c) => c.met).length : 0;
    const sheetTab = (key: Sheet, label: React.ReactNode) => (
      <button
        type="button"
        aria-expanded={sheet === key}
        data-testid={`dock-${key}`}
        onClick={() => setSheet(sheet === key ? null : key)}
      >
        {label}
      </button>
    );
    return (
      <UiContext.Provider value={ui}>
        <main className={`app game phone ${phone}${holding ? " holding" : ""}`}>
          <Board
            view={view}
            act={phoneAct}
            playing={playing}
            won={result && !waiting ? winningCourt(view) : undefined}
            hand={false}
            marks={marks}
          />
          {(menuOpen || sheet) && (
            <div
              className="scrim"
              aria-hidden="true"
              onClick={() => {
                setMenuOpen(false);
                setSheet(null);
              }}
            />
          )}
          <div className="menu">
            <button
              type="button"
              className="menu-button"
              aria-label="Menu"
              aria-expanded={menuOpen}
              data-testid="menu"
              onClick={() => setMenuOpen(!menuOpen)}
            >
              <svg viewBox="0 0 20 20" aria-hidden="true">
                <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
            {menuOpen && (
              <div className="menu-panel" onClick={(e) => e.target instanceof HTMLButtonElement && setMenuOpen(false)}>
                {speedControl}
                <button type="button" data-testid="show-rules" onClick={() => setRulesOpen(true)}>
                  Rules
                </button>
                <button type="button" onClick={toSetup}>
                  New game
                </button>
                <FrameControls />
                <Credit />
              </div>
            )}
          </div>
          <div className="dock">
            {sheet && (
              <div className="sheet" data-testid="sheet">
                {sheet === "agenda" && myAgenda && <AgendaTracker agenda={myAgenda} />}
                {sheet === "log" && logList}
                {sheet === "discard" && <DiscardPile view={view} dropLive={false} />}
              </div>
            )}
            {shown.coach && <CoachPanel coach={shown.coach} foldable />}
            <div className="dock-question">{question}</div>
            {holding && (
              <div className="dock-offers">
                {offers && offerButtons(offers)}
                <button type="button" className="put-down" data-testid="put-down" onClick={putDown}>
                  Put it down
                </button>
              </div>
            )}
            {error && <p className="error">{error}</p>}
            {view.you >= 0 && <Hand view={view} act={phoneAct} marks={marks} />}
            <nav className="dock-tabs" aria-label="Agenda, log and discard pile">
              {myAgenda &&
                sheetTab(
                  "agenda",
                  <>
                    Agenda <small className={myAgenda.met ? "met" : ""}>{met}/{myAgenda.status.length}</small>
                  </>,
                )}
              {sheetTab("log", "Log")}
              {sheetTab(
                "discard",
                <>
                  Discard <small>{view.discard}</small>
                </>,
              )}
            </nav>
          </div>
          {overlays}
        </main>
      </UiContext.Provider>
    );
  }

  return (
    <UiContext.Provider value={ui}>
      <main className="app game">
        <Board
          view={view}
          act={act}
          playing={playing}
          won={result && !waiting ? winningCourt(view) : undefined}
          marks={marks}
        />
        <div className="rail">
          <aside className="side">
            <div className="controls">
              {speedControl}
              <button type="button" data-testid="show-rules" onClick={() => setRulesOpen(true)}>
                Rules
              </button>
              <button type="button" onClick={toSetup}>
                New game
              </button>
            </div>
            <div className="controls frame">
              <FrameControls />
            </div>

            {shown.coach && <CoachPanel coach={shown.coach} />}
            {question}
            {/* Once the game is over the pile says nothing; the reveal takes its room. */}
            {!(result && !waiting) && <DiscardPile view={view} dropLive={dropping.has("discard")} />}
            {error && <p className="error">{error}</p>}
            {hovered && !result && (
              <div className="preview" aria-hidden="true">
                <CardDetail card={hovered} />
              </div>
            )}
          </aside>
          {tabs}
        </div>
        <Credit />
        {overlays}
      </main>
    </UiContext.Provider>
  );
}
