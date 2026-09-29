import type { CSSProperties } from "react";
import type { Result, View } from "../protocol";
import { useUi } from "../art";
import { playerName, seatColour } from "../names";

interface Props {
  view: View;
  result: Result;
  saved: number | null; // games kept in this browser; null if storage is off
  copied: boolean;
  onPlayAgain(): void;
  onNewTable(): void;
  onCopy(): void;
  onDownloadRecord(): void;
  onExport(): void;
  /** Your guesses at rivals' agendas, to mark right or wrong. */
  guesses?: Record<number, string>;
}

export function headline(view: View, result: Result): string {
  if (result.timeout) return "Chaos grips the empire";
  if (result.winners.includes(view.you)) return result.winners.length > 1 ? "You share the win" : "You win";
  const names = result.winners.map((w) => playerName(view, w));
  return `${names.join(" and ")} ${names.length > 1 ? "win" : "wins"}`;
}

/**
 * Every seated courtier who won the game, with the colour of the winner they
 * won it for. The board lights these up.
 */
export function winningCourt(view: View): Map<number, string> {
  const out = new Map<number, string>();
  for (const w of view.winners) {
    for (const uid of view.players[w]?.agenda?.seated ?? []) {
      if (!out.has(uid)) out.set(uid, seatColour(w));
    }
  }
  return out;
}

// The end of the game, in the rail where the question usually is: the winner
// turns their agenda over, and the court that won it lights up on the board.
export function GameOver(props: Props) {
  const { view, result, saved, copied } = props;
  const { art } = useUi();
  const rounds = Math.ceil(result.turns / view.players.length);

  return (
    <section className="prompt over" data-testid="game-over" aria-labelledby="over-title">
      <h2 id="over-title">{headline(view, result)}</h2>
      {result.timeout && (
        <p className="no-winner">
          Without effective council, the young king grows indulgent and tyrannical, and the kingdom slips into chaos.
          Everyone loses.
        </p>
      )}
      <p className="muted">
        {result.timeout ? `${rounds} ${rounds === 1 ? "round" : "rounds"} passed` : "After"} {result.timeout ? `(${result.turns} turns)` : `${result.turns} turns (${rounds} rounds)`}
        {result.timeout ? " with no agenda met." : "."}
      </p>

      {result.winners.map((w) => {
        const agenda = view.players[w]?.agenda;
        if (!agenda) return null;
        const src = art.agenda(agenda.name);
        const seated = agenda.seated.length;
        return (
          <figure
            key={w}
            className="revealed-agenda"
            data-testid="revealed-agenda"
            style={{ "--seat": seatColour(w) } as CSSProperties}
          >
            <div className="flip" aria-hidden="true">
              <div className="side back">{art.back ? <img src={art.back} alt="" /> : null}</div>
              <div className="side front">{src ? <img src={src} alt="" /> : <span className="text-face">{agenda.name}</span>}</div>
            </div>
            <figcaption>
              <span className="who">{w === view.you ? "Your agenda" : `${playerName(view, w)} reveals`}</span>
              <strong>{agenda.name}</strong>
              <span className="muted">
                {seated} {seated === 1 ? "courtier" : "courtiers"} in the inner circle carried it
              </span>
            </figcaption>
          </figure>
        );
      })}

      <AllAgendas view={view} result={result} guesses={props.guesses ?? {}} />

      <div className="buttons">
        <button type="button" className="primary" onClick={props.onPlayAgain} data-testid="play-again">
          Play again
        </button>
        <button type="button" onClick={props.onNewTable}>
          Change the table
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
    </section>
  );
}

// Every agenda at the table, turned over: what each player was after, and how
// near the board came to giving it them. The part of a hidden-agenda game
// worth seeing twice.
function AllAgendas({ view, result, guesses }: { view: View; result: Result; guesses: Record<number, string> }) {
  const others = view.players.filter((p) => !result.winners.includes(p.seat) && p.agenda);
  const called = view.players.filter((p) => guesses[p.seat] && p.agenda);
  if (!others.length && !called.length) return null;
  return (
    <section className="all-agendas" data-testid="all-agendas" aria-label="Every agenda at the table">
      <h3>{result.winners.length ? "What everyone else wanted" : "What everyone wanted"}</h3>
      <ul>
        {others.map((p) => {
          const agenda = p.agenda!;
          const met = agenda.status.filter((c) => c.met).length;
          const need = agenda.status.reduce((n, c) => n + c.need, 0);
          const have = agenda.status.reduce((n, c) => n + Math.min(c.have, c.need), 0);
          const nearest = agenda.status.find((c) => !c.met);
          return (
            <li key={p.seat} style={{ "--seat": seatColour(p.seat) } as CSSProperties}>
              <span className="who">{p.seat === view.you ? "You" : playerName(view, p.seat)}</span>
              <strong>{agenda.name}</strong>
              <span className="bar" aria-hidden="true">
                <span style={{ width: `${(have / need) * 100}%` }} />
              </span>
              <small className="muted">
                {met} of {agenda.status.length} met
                {nearest ? ` \u00b7 short: ${nearest.label.toLowerCase()} (${nearest.have}/${nearest.need})` : ""}
              </small>
            </li>
          );
        })}
      </ul>
      {called.length > 0 && (
        <p className="guesses" data-testid="guesses">
          Your reads:{" "}
          {called.map((p, i) => {
            const right = guesses[p.seat] === p.agenda!.name;
            return (
              <span key={p.seat} className={right ? "right" : "wrong"}>
                {i > 0 && ", "}
                {playerName(view, p.seat)} {right ? "✓" : `✗ (you guessed ${guesses[p.seat]})`}
              </span>
            );
          })}
        </p>
      )}
    </section>
  );
}
