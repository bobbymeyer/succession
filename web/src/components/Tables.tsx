// The table, laid out for the screen it is on. A desktop keeps the board
// beside a rail of panels; a phone fits one screen: the board, with a menu in
// its corner, over a dock that holds the question, your hand, and tabs that
// pull up your agenda, the log and the discard pile.

import { useState, type ReactNode } from "react";
import type { Card } from "../protocol";
import type { GameFlow } from "../useGameFlow";
import type { Play } from "../usePlay";
import { AgendaTracker } from "./AgendaTracker";
import { Board, Hand, type Interaction, type Marks, type Suspicions } from "./Board";
import { CoachPanel } from "./Coach";
import { Credit } from "./Credit";
import { FrameControls } from "./Frame";
import { winningCourt } from "./GameOver";
import { CardDetail } from "./Inspect";
import { Offers } from "./Offers";
import { AgendaAndLog, GameLog } from "./SidePanels";
import { DiscardPile } from "./Status";

export interface TableProps {
  flow: GameFlow;
  play: Play;
  marks: Marks;
  suspicions: Suspicions;
  /** The question panel (Question). */
  question: ReactNode;
  /** What is laid over the table (Overlays). */
  overlays: ReactNode;
  speedControl: ReactNode;
  onRules(): void;
  onNewGame(): void;
  /** A drop target lit under a dragged card. */
  dropLive(key: string): boolean;
}

export function DesktopTable({ flow, play, marks, suspicions, question, overlays, speedControl, onRules, onNewGame, dropLive, hovered }: TableProps & { hovered: Card | null }) {
  const shown = flow.shown!;
  const view = shown.view;
  return (
    <main className={`app game${flow.liveEvent ? " event-live" : ""}`}>
      <Board view={view} act={play.act} playing={flow.playing} won={flow.over ? winningCourt(view) : undefined} marks={marks} suspicions={suspicions} />
      <div className="rail">
        <aside className="side">
          <div className="controls">
            {speedControl}
            <button type="button" data-testid="show-rules" onClick={onRules}>
              Rules
            </button>
            <button type="button" onClick={onNewGame}>
              New game
            </button>
          </div>
          <div className="controls frame">
            <FrameControls />
          </div>

          {shown.coach && <CoachPanel coach={shown.coach} />}
          {question}
          {/* Once the game is over the pile says nothing; the reveal takes its room. */}
          {!flow.over && <DiscardPile view={view} dropLive={dropLive("discard")} />}
          {flow.error && <p className="error">{flow.error}</p>}
          {hovered && !shown.result && (
            <div className="preview" aria-hidden="true">
              <CardDetail card={hovered} />
            </div>
          )}
        </aside>
        <AgendaAndLog view={view} log={flow.log} />
      </div>
      <Credit />
      {overlays}
    </main>
  );
}

type Sheet = "agenda" | "log" | "discard" | null;

export function PhoneTable({ flow, play, marks, suspicions, question, overlays, speedControl, onRules, onNewGame, orientation }: TableProps & { orientation: string }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [sheet, setSheet] = useState<Sheet>(null);
  const shown = flow.shown!;
  const view = shown.view;
  const myAgenda = view.you >= 0 ? view.players[view.you].agenda : null;
  const met = myAgenda ? myAgenda.status.filter((c) => c.met).length : 0;
  // A picked-up card's choices sit in the dock, not over the card, where
  // they would cover the question; with a way to put the card down.
  const act: Interaction = { ...play.act, popover: () => null };
  const sheetTab = (key: Sheet, label: ReactNode) => (
    <button type="button" aria-expanded={sheet === key} data-testid={`dock-${key}`} onClick={() => setSheet(sheet === key ? null : key)}>
      {label}
    </button>
  );
  return (
    <main className={`app game phone ${orientation}${play.holding ? " holding" : ""}${flow.liveEvent ? " event-live" : ""}`}>
      <Board view={view} act={act} playing={flow.playing} won={flow.over ? winningCourt(view) : undefined} hand={false} marks={marks} suspicions={suspicions} />
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
        <button type="button" className="menu-button" aria-label="Menu" aria-expanded={menuOpen} data-testid="menu" onClick={() => setMenuOpen(!menuOpen)}>
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
        {menuOpen && (
          <div className="menu-panel" onClick={(e) => e.target instanceof HTMLButtonElement && setMenuOpen(false)}>
            {speedControl}
            <button type="button" data-testid="show-rules" onClick={onRules}>
              Rules
            </button>
            <button type="button" onClick={onNewGame}>
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
            {sheet === "log" && <GameLog log={flow.log} />}
            {sheet === "discard" && <DiscardPile view={view} dropLive={false} />}
          </div>
        )}
        {shown.coach && <CoachPanel coach={shown.coach} foldable />}
        <div className="dock-question">{question}</div>
        {play.holding && (
          <div className="dock-offers">
            {play.offers && <Offers offers={play.offers} />}
            <button type="button" className="put-down" data-testid="put-down" onClick={play.putDown}>
              Put it down
            </button>
          </div>
        )}
        {flow.error && <p className="error">{flow.error}</p>}
        {view.you >= 0 && <Hand view={view} act={act} marks={marks} />}
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
  );
}
