import { useEffect, useRef } from "react";
import type { Result, View } from "../protocol";
import { useUi } from "../art";
import { playerName } from "../names";

interface Props {
  open: boolean;
  view: View;
  result: Result;
  saved: number | null; // games kept in this browser; null if storage is off
  copied: boolean;
  onClose(): void;
  onPlayAgain(): void;
  onNewTable(): void;
  onCopy(): void;
  onDownloadRecord(): void;
  onExport(): void;
}

export function headline(view: View, result: Result): string {
  if (result.timeout) return "No one takes the throne";
  if (result.winners.includes(view.you)) return result.winners.length > 1 ? "You share the win" : "You win";
  const names = result.winners.map((w) => playerName(view, w));
  return `${names.join(" and ")} ${names.length > 1 ? "win" : "wins"}`;
}

export function GameOver(props: Props) {
  const { open, view, result, saved, copied } = props;
  const { art, inspect } = useUi();
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = dialog.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  const rounds = Math.ceil(result.turns / view.players.length);
  return (
    <dialog ref={dialog} className="game-over" data-testid="game-over-dialog" onClose={props.onClose} aria-labelledby="over-title">
      <h2 id="over-title">{headline(view, result)}</h2>
      <p className="muted">
        After {result.turns} turns ({rounds} rounds).
        {result.timeout ? " The turn limit ran out with no agenda met." : ""}
      </p>

      <ul className="standings">
        {view.players.map((p) => {
          const won = result.winners.includes(p.seat);
          const src = p.agenda ? art.agenda(p.agenda.name) : null;
          return (
            <li key={p.seat} className={won ? "won" : ""}>
              {src ? <img src={src} alt="" /> : null}
              <div>
                <strong>{playerName(view, p.seat)}</strong>
                <div>{p.agenda?.name}</div>
                {won && <span className="badge">Winner</span>}
              </div>
            </li>
          );
        })}
      </ul>

      <h3>The court at the end</h3>
      <ol className="final-court">
        {view.seats.map((s) => {
          const src = s.courtier ? art.card(s.courtier.name) : null;
          return (
            <li key={s.seat}>
              {s.courtier ? (
                <button type="button" className="thumb" onClick={() => inspect(s.courtier!)} aria-label={`Look at ${s.courtier.name}`}>
                  {src ? <img src={src} alt="" /> : <span>{s.courtier.name}</span>}
                </button>
              ) : (
                <span className="thumb vacant" />
              )}
              <small>{s.seat}</small>
            </li>
          );
        })}
      </ol>

      <div className="buttons">
        <button type="button" className="primary" onClick={props.onPlayAgain} data-testid="play-again">
          Play again
        </button>
        <button type="button" onClick={props.onNewTable}>
          Change the table
        </button>
        <button type="button" onClick={props.onClose}>
          Look at the board
        </button>
      </div>

      <details className="export">
        <summary>Save this game</summary>
        <p className="muted">
          A game record replays this exact game, move for move -- paste it into "Load a saved game", or run{" "}
          <code>python -m succession play --replay game.json</code>. Handy for a bug report.
        </p>
        <div className="buttons">
          <button type="button" onClick={props.onCopy}>
            {copied ? "Copied" : "Copy game record"}
          </button>
          <button type="button" onClick={props.onDownloadRecord}>
            Download game record
          </button>
        </div>
        {saved !== null && (
          <>
            <p className="muted">
              {saved} finished {saved === 1 ? "game is" : "games are"} kept in this browser. The CSV is the simulator's own
              log format: <code>python -m succession analyze games.csv</code>.
            </p>
            <div className="buttons">
              <button type="button" onClick={props.onExport} disabled={!saved} data-testid="export">
                Download games as CSV
              </button>
            </div>
          </>
        )}
      </details>
    </dialog>
  );
}
