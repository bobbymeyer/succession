import { useEffect, useRef, useState } from "react";
import type { Card, EventReport, Prompt, View } from "../protocol";
import { useUi } from "../art";
import { playerName, readableLog, seatColour } from "../names";

// An event hits the whole table, so the whole table stops for it: the card,
// what it does, and what it just did to each player. Play goes on from
// Continue.
export function EventModal({ report, view, onContinue }: { report: EventReport; view: View; onContinue(): void }) {
  const { art, inspect } = useUi();
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = dialog.current;
    if (d && !d.open) d.showModal();
  }, []);

  const src = art.card(report.card.name);
  const who = report.player === view.you ? "You play" : `${playerName(view, report.player)} plays`;

  const row = (label: string, cards: Card[], tone: string) =>
    cards.length > 0 && (
      <div className={`event-cards ${tone}`}>
        <h3>{label}</h3>
        <ul>
          {cards.map((c) => {
            const face = art.card(c.name);
            return (
              <li key={c.uid}>
                <button type="button" className="thumb" onClick={() => inspect(c)} aria-label={`Look at ${c.name}`} title={c.name}>
                  {face ? <img src={face} alt="" /> : <span>{c.name}</span>}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    );

  return (
    // Escape carries on too.
    <dialog
      ref={dialog}
      className="event-modal"
      data-testid="event"
      onClose={onContinue}
      aria-labelledby="event-title"
      style={{ "--seat": seatColour(report.player) } as React.CSSProperties}
    >
      <div className="event-art">{src ? <img src={src} alt="" /> : <span className="text-face">{report.card.name}</span>}</div>
      <div className="event-text">
        <span className="kicker">Event · {who}</span>
        <h2 id="event-title">{report.card.name}</h2>
        <p className="event-summary">{report.summary}</p>
        <ul className="event-effects">
          {report.effects.map((e, i) => (
            <li key={i} className={e.tone} style={{ animationDelay: `${600 + i * 180}ms` }}>
              {readableLog(view, e.text)}
            </li>
          ))}
        </ul>
        {row("Fallen", report.fallen, "loss")}
        {row("Spared", report.spared, "gain")}
        {row("Thrown away", report.discarded, "loss")}
        <form method="dialog">
          <button type="submit" className="primary" data-testid="event-continue" autoFocus>
            Continue
          </button>
        </form>
      </div>
    </dialog>
  );
}

/** How long an event that needs your choice is announced before it asks. */
export const ANNOUNCE_MS = 2600;

// An event that stops to ask you something (name a courtier, discard) is
// announced first, briefly: the card, what it does, and what it wants from
// you. It closes itself, or on a click, and the question is waiting behind it.
export function EventAnnouncement({
  prompt,
  actor,
  view,
  onDone,
}: {
  prompt: Prompt & { kind: "courtier" | "discard" };
  actor: number;
  view: View;
  onDone(): void;
}) {
  const { art } = useUi();
  const dialog = useRef<HTMLDialogElement>(null);
  const [closing, setClosing] = useState(false);
  useEffect(() => {
    const d = dialog.current;
    if (d && !d.open) d.showModal();
    const t = window.setTimeout(() => setClosing(true), ANNOUNCE_MS);
    return () => window.clearTimeout(t);
  }, []);
  useEffect(() => {
    if (!closing) return;
    const t = window.setTimeout(() => dialog.current?.close(), 260);
    return () => window.clearTimeout(t);
  }, [closing]);

  const card = prompt.card!;
  const src = art.card(card.name);
  const who = actor === view.you ? "You play" : actor >= 0 ? `${playerName(view, actor)} plays` : "An event";
  const ask = prompt.kind === "courtier" ? "Name a courtier to die." : "Choose what to discard.";

  return (
    <dialog
      ref={dialog}
      className={`event-modal announce${closing ? " closing" : ""}`}
      data-testid="event-announce"
      onClose={onDone}
      onClick={() => setClosing(true)}
      aria-labelledby="announce-title"
      style={{ "--seat": seatColour(Math.max(actor, 0)) } as React.CSSProperties}
    >
      <div className="event-art">{src ? <img src={src} alt="" /> : <span className="text-face">{card.name}</span>}</div>
      <div className="event-text">
        <span className="kicker">Event · {who}</span>
        <h2 id="announce-title">{card.name}</h2>
        <p className="event-summary">{prompt.summary}</p>
        <p className="event-ask">
          <strong>Your choice:</strong> {ask} Everyone chooses at once.
        </p>
        <div className="announce-timer" style={{ animationDuration: `${ANNOUNCE_MS}ms` }} aria-hidden="true" />
      </div>
    </dialog>
  );
}
