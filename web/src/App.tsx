import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Engine } from "./engine";
import { loadArt, NO_ART, UiContext, type Art, type Ui } from "./art";
import { FIRST_GAME_TABLE } from "./firstGame";
import { clearGames, download, savedGames } from "./history";
import { warmOffline } from "./offline";
import type { Card, GameRecord, TableOptions } from "./protocol";
import { useDrag } from "./useDrag";
import { useGameFlow } from "./useGameFlow";
import { usePhone } from "./usePhone";
import { usePlay } from "./usePlay";
import { marksFor, type Suspicions } from "./components/Board";
import { Credit } from "./components/Credit";
import { GameOver } from "./components/GameOver";
import { Intro, introSeen } from "./components/Intro";
import { Overlays } from "./components/Overlays";
import { Question } from "./components/Question";
import { Rules } from "./components/Rules";
import { Setup } from "./components/Setup";
import { SpeedControl } from "./components/SidePanels";
import { DesktopTable, PhoneTable, type TableProps } from "./components/Tables";

// The page: the engine booting, the title screen, and the table. What the
// table is waiting on is worked out in flow.ts and paced by useGameFlow;
// building a move by hand is usePlay; the layouts are components/Tables.
export function App() {
  const engine = useMemo(() => new Engine(), []);
  const [options, setOptions] = useState<TableOptions | null>(null);
  // The story plays on a first visit, over the engine's boot.
  const [intro, setIntro] = useState(() => !introSeen());
  const [fatal, setFatal] = useState<string | null>(null);
  const [rulesOpen, setRulesOpen] = useState(false);
  const phone = usePhone();
  // Your private guesses at rivals' agendas; a new deal forgets them.
  const [guesses, setGuesses] = useState<Record<number, string>>({});
  const [copied, setCopied] = useState(false);

  const [art, setArt] = useState<Art>(NO_ART);
  const [inspecting, setInspecting] = useState<Card | null>(null);
  const [hovered, setHovered] = useState<Card | null>(null);
  const looking = inspecting?.uid ?? null;
  const ui = useMemo<Ui>(() => ({ art, inspect: setInspecting, hover: setHovered, looking }), [art, looking]);

  useEffect(() => {
    engine.ready.then((r) => setOptions(r.options)).catch((e: Error) => setFatal(e.message));
    // Without pictures the game still plays, drawn as type.
    loadArt().then(setArt, () => setArt(NO_ART));
  }, [engine]);
  // Once the engine and the art are in, the offline cache takes the rest.
  useEffect(() => {
    if (options && art !== NO_ART) warmOffline(art.offline);
  }, [options, art]);

  // Whatever is picked up is put down when a request comes back.
  const putDown = useRef(() => {});
  const flow = useGameFlow(engine, art, {
    onRestart: () => setGuesses({}),
    onSettle: () => {
      putDown.current();
      setCopied(false);
    },
  });
  const drag = useDrag();
  const view = flow.shown?.view ?? null;
  const { play, reset } = usePlay(flow, view, (choice) => flow.send({ type: "answer", choice }), drag, () => setInspecting(null));
  putDown.current = reset;

  const exportCsv = useCallback(async () => {
    try {
      download("succession-games.csv", await engine.exportCsv(savedGames()), "text/csv");
    } catch (e) {
      flow.setError((e as Error).message);
    }
  }, [engine, flow]);

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
  const rules = rulesOpen && <Rules options={options} onClose={() => setRulesOpen(false)} />;
  if (!view) {
    return (
      <UiContext.Provider value={ui}>
        <main className="app">
          <Setup
            options={options}
            saved={flow.saved}
            onDeal={(players, seed, deal) => flow.send({ type: "new", players, seed, deal }, true)}
            onTutorial={() => flow.send({ type: "tutorial" }, true)}
            onLoad={(record: GameRecord) => flow.send({ type: "load", record }, true)}
            onExport={exportCsv}
            onClear={() => {
              clearGames();
              flow.refreshSaved();
            }}
            onIntro={() => setIntro(true)}
            onRules={() => setRulesOpen(true)}
          />
          {rules}
          {flow.error && <p className="error">{flow.error}</p>}
          <Credit />
        </main>
      </UiContext.Provider>
    );
  }

  // Lit on the table: the moves that win you the game now, and the courtier a rival attacks.
  const marks = marksFor(
    view,
    new Set(play.winning.flatMap((a) => [a.card, a.courtier].filter((u): u is number => u !== null))),
    flow.block ? new Set([flow.block.about.uid]) : new Set(),
  );
  const suspicions: Suspicions = {
    agendas: options.rules.agendas.map((a) => a.name),
    guess: guesses,
    onGuess: (seat, agenda) =>
      setGuesses((g) => {
        const next = { ...g };
        if (agenda) next[seat] = agenda;
        else delete next[seat];
        return next;
      }),
  };

  const over = flow.over;
  const gameOver = over && (
    <GameOver
      view={view}
      result={over}
      saved={flow.saved}
      copied={copied}
      onPlayAgain={() => {
        // The same table again, freshly dealt; after the tutorial, a real game at the default table.
        const players = over.record.scenario ? ["human", ...FIRST_GAME_TABLE] : (over.record.config.players as string[]);
        flow.send({ type: "new", players }, true);
      }}
      onNewTable={flow.toSetup}
      onCopy={async () => {
        try {
          await navigator.clipboard.writeText(JSON.stringify(over.record));
          setCopied(true);
        } catch {
          flow.setError("Couldn't copy to the clipboard.");
        }
      }}
      onDownloadRecord={() => download(`succession-game-${over.record.seed}.json`, JSON.stringify(over.record, null, 1), "application/json")}
      onExport={exportCsv}
      guesses={guesses}
    />
  );

  const table: TableProps = {
    flow,
    play,
    marks,
    suspicions,
    question: <Question flow={flow} play={play} phone={phone !== null} gameOver={gameOver} />,
    overlays: (
      <Overlays
        flow={flow}
        play={play}
        options={options}
        rulesOpen={rulesOpen}
        onCloseRules={() => setRulesOpen(false)}
        inspecting={inspecting}
        onInspect={setInspecting}
        phone={phone !== null}
      />
    ),
    speedControl: <SpeedControl speed={flow.speed} onChange={flow.changeSpeed} />,
    onRules: () => setRulesOpen(true),
    onNewGame: flow.toSetup,
    dropLive: drag.dropLive,
  };
  return (
    <UiContext.Provider value={ui}>
      {phone ? <PhoneTable {...table} orientation={phone} /> : <DesktopTable {...table} hovered={hovered} />}
    </UiContext.Provider>
  );
}
