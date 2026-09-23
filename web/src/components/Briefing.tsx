import { useEffect, useRef } from "react";
import type { View } from "../protocol";
import { useUi } from "../art";
import { playerName } from "../names";

// The start of a round: the table is dealt and nobody has moved. You turn
// your agenda over, read what it asks, and begin when you are ready; the bots
// wait for you.
export function Briefing({ view, onBegin }: { view: View; onBegin(): void }) {
  const { art } = useUi();
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = dialog.current;
    if (d && !d.open) d.showModal();
  }, []);

  const agenda = view.players[view.you]?.agenda;
  if (!agenda) return null;
  const src = art.agenda(agenda.name);
  const first = view.current === view.you ? "You move first." : `${playerName(view, view.current)} moves first.`;

  return (
    // Escape begins too: there is nothing else to go back to.
    <dialog ref={dialog} className="briefing" data-testid="briefing" onClose={onBegin} aria-labelledby="briefing-title">
      <div className="agenda-flip" aria-hidden="true">
        <div className="side back">{art.back ? <img src={art.back} alt="" /> : null}</div>
        <div className="side front">{src ? <img src={src} alt="" /> : <span className="text-face">{agenda.name}</span>}</div>
      </div>
      <div className="briefing-text">
        <span className="kicker">Your secret agenda</span>
        <h2 id="briefing-title">{agenda.name}</h2>
        <p className="muted">Win by making the inner circle look like this, then revealing it:</p>
        <ul className="briefing-clauses">
          {agenda.status.map((c) => (
            <li key={c.label}>{c.label}</li>
          ))}
        </ul>
        <p className="muted">
          Nobody else can see it. {first}
        </p>
        <form method="dialog">
          <button type="submit" className="primary" data-testid="begin" autoFocus>
            Begin the round
          </button>
        </form>
      </div>
    </dialog>
  );
}
