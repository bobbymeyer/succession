import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Engine } from "./engine";
import { loadArt, NO_ART, preload, UiContext, type Art, type Ui } from "./art";
import { build, cardIsLive, choose, clickCard, FIELDS, seatIsLive, type Selection } from "./moves";
import type { Card, GameRecord, Request, TableOptions, Update } from "./protocol";
import { playerName, readableLog, visibleCards } from "./names";
import { Board, NO_INTERACTION, type Interaction } from "./components/Board";
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

  const pump = useCallback(() => {
    timer.current = null;
    const next = queue.current.shift();
    if (!next) return;
    setShown(next);
    setLog((l) => [...l, ...next.log.map((text) => ({ text, view: next.view }))]);
    setPending(queue.current.length);
    if (queue.current.length) {
      const delay = next.prompt ? 0 : SPEEDS[speedRef.current];
      timer.current = window.setTimeout(pump, delay);
    }
  }, []);

  const send = useCallback(
    async (request: Request, fresh = false) => {
      if (fresh) preload(art);
      setBusy(true);
      setError(null);
      try {
        const updates = await engine.send(request);
        if (fresh) {
          if (timer.current !== null) window.clearTimeout(timer.current);
          timer.current = null;
          queue.current = [];
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
            onDeal={(players, seed) => send({ type: "new", players, seed }, true)}
            onLoad={(record: GameRecord) => send({ type: "load", record }, true)}
          />
          {error && <p className="error">{error}</p>}
        </main>
      </UiContext.Provider>
    );
  }

  const { view, prompt, result } = shown;
  const waiting = pending > 0 || busy;
  const cards = visibleCards(view);
  const turnPrompt = !waiting && prompt?.kind === "turn" ? prompt : null;
  const pickPrompt = !waiting && prompt && prompt.kind !== "turn" ? prompt : null;
  const builder = turnPrompt ? build(turnPrompt.options, selection) : null;

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
          <button type="button" onClick={() => setShown(null)}>
            New game
          </button>
        </div>

        {result ? (
          <div className="prompt over" data-testid="game-over">
            <div className="winners">
              {result.winners.map((w) => {
                const agenda = view.players[w].agenda;
                const src = agenda && art.agenda(agenda.name);
                return src ? <img key={w} src={src} alt={agenda!.name} /> : null;
              })}
            </div>
            <h2>
              {result.timeout
                ? "No winner"
                : result.winners.includes(view.you)
                  ? "You win"
                  : `${result.winners.map((w) => playerName(view, w)).join(" and ")} ${result.winners.length > 1 ? "win" : "wins"}`}
            </h2>
            <ul>
              {view.players.map((p) => (
                <li key={p.seat}>
                  {playerName(view, p.seat)}: {p.agenda?.name}
                  {result.winners.includes(p.seat) ? " (won)" : ""}
                </li>
              ))}
            </ul>
            <p>After {result.turns} turns.</p>
            <div className="buttons">
              <button type="button" className="primary" onClick={() => setShown(null)}>
                New game
              </button>
              <button type="button" onClick={copyRecord}>
                {copied ? "Copied" : "Copy game record"}
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
          <div className="prompt">
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

      <section className="log" aria-label="Game log">
          <h2>Log</h2>
          <ol reversed>
            {log
              .slice()
              .reverse()
              .map((line, i) => (
                <li key={log.length - i}>{readableLog(line.view, line.text)}</li>
              ))}
          </ol>
      </section>
      </div>
      <Inspect card={inspecting} onClose={() => setInspecting(null)} />
    </main>
    </UiContext.Provider>
  );
}
