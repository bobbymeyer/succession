import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Engine } from "./engine";
import { loadArt, NO_ART, preload, UiContext, type Art, type Ui } from "./art";
import { EMPTY, measure, play, type Snapshot } from "./flip";
import { clearGames, download, saveGame, savedGames } from "./history";
import { build, cardIsLive, choose, clickCard, FIELDS, seatIsLive, type Selection } from "./moves";
import type { Card, GameRecord, GameRequest, TableOptions, Update } from "./protocol";
import { playerName, readableLog, visibleCards } from "./names";
import { AgendaTracker } from "./components/AgendaTracker";
import { Board, NO_INTERACTION, type Interaction } from "./components/Board";
import { GameOver, headline } from "./components/GameOver";
import { FrameControls } from "./components/Frame";
import { CardDetail, Inspect } from "./components/Inspect";
import { PickPanel, TurnPanel } from "./components/PromptPanel";
import { Setup } from "./components/Setup";

const SPEEDS = { Slow: 1200, Normal: 600, Fast: 200, Instant: 0 } as const;
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
  return Math.min(600, SPEEDS[speed] * 0.7);
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
  const [overOpen, setOverOpen] = useState(false);
  const [tab, setTab] = useState<"agenda" | "log">("agenda");
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
  const before = useRef<{ snapshot: Snapshot; actor: number } | null>(null);
  const fresh = useRef(false);

  const pump = useCallback(() => {
    timer.current = null;
    const next = queue.current.shift();
    if (!next) return;
    before.current = { snapshot: fresh.current ? EMPTY : measure(), actor: next.actor };
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
    if (from && shown) play(from.snapshot, from.actor, shown.view.you, glide(speedRef.current));
  }, [shown]);

  // A finished game is kept for export, and its results come up once the
  // last bot move has played out.
  const result = shown?.result ?? null;
  useEffect(() => {
    if (!result || pending > 0) return;
    setSaved(saveGame(result.record) ? savedGames().length : null);
    setOverOpen(true);
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
          setOverOpen(false);
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
    setOverOpen(false);
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
        </main>
      </UiContext.Provider>
    );
  }

  const { view, prompt } = shown;
  const waiting = pending > 0 || busy;
  const cards = visibleCards(view);
  const turnPrompt = !waiting && prompt?.kind === "turn" ? prompt : null;
  const pickPrompt = !waiting && prompt && prompt.kind !== "turn" ? prompt : null;
  const builder = turnPrompt ? build(turnPrompt.options, selection) : null;
  const latest = log.length ? readableLog(log[log.length - 1].view, log[log.length - 1].text) : null;

  let act: Interaction = NO_INTERACTION;
  if (turnPrompt && builder) {
    act = {
      cardLive: (uid) => cardIsLive(turnPrompt.options, builder, uid),
      cardSelected: (uid) => selection.card === uid || selection.courtier === uid || selection.sacrifice === uid,
      onCard: (uid) => {
        const next = clickCard(turnPrompt.options, builder, uid);
        if (next) setSelection(next);
      },
      seatLive: (seat) => seatIsLive(builder, seat),
      seatSelected: (seat) => selection.seat === seat,
      onSeat: (seat) => setSelection(choose(builder, seat)),
    };
  } else if (pickPrompt) {
    const uids = pickPrompt.options.map((c) => c.uid);
    act = {
      ...NO_INTERACTION,
      cardLive: (uid) => uids.includes(uid),
      cardSelected: (uid) => picked === uid,
      onCard: (uid) => setPicked(uid),
    };
  }

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
        <Board view={view} act={act} />
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
              <div className="prompt over" data-testid="game-over">
                <h2>{headline(view, result)}</h2>
                <div className="buttons">
                  <button type="button" className="primary" onClick={() => setOverOpen(true)}>
                    Results
                  </button>
                  <button type="button" onClick={playAgain}>
                    Play again
                  </button>
                </div>
              </div>
            ) : turnPrompt && builder ? (
              <TurnPanel
                view={view}
                prompt={turnPrompt}
                builder={builder}
                cards={cards}
                onChoose={(value) => setSelection(choose(builder, value))}
                onSelectAction={(a) => setSelection(Object.fromEntries(FIELDS.map((f) => [f, a[f]])))}
                onConfirm={() => builder.chosen && send({ type: "answer", choice: builder.chosen.index })}
                onReset={() => setSelection({})}
              />
            ) : pickPrompt ? (
              <PickPanel
                prompt={pickPrompt}
                picked={picked}
                onPick={setPicked}
                onConfirm={() => picked !== null && send({ type: "answer", choice: picked })}
              />
            ) : (
              <div className="prompt" aria-live="polite">
                {latest && <p className="latest">{latest}</p>}
                <p className="thinking">{playerName(view, view.current)} to play…</p>
              </div>
            )}
            {error && <p className="error">{error}</p>}
            {hovered && (
              <div className="preview" aria-hidden="true">
                <CardDetail card={hovered} />
              </div>
            )}
          </aside>
          {tabs}
        </div>
        <Inspect card={inspecting} onClose={() => setInspecting(null)} />
        {result && (
          <GameOver
            open={overOpen && !waiting}
            view={view}
            result={result}
            saved={saved}
            copied={copied}
            onClose={() => setOverOpen(false)}
            onPlayAgain={playAgain}
            onNewTable={toSetup}
            onCopy={copyRecord}
            onDownloadRecord={() =>
              download(`succession-game-${result.record.seed}.json`, JSON.stringify(result.record, null, 1), "application/json")
            }
            onExport={exportCsv}
          />
        )}
      </main>
    </UiContext.Provider>
  );
}
