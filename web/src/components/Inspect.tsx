import { useEffect, useRef } from "react";
import type { Card } from "../protocol";
import { useUi } from "../art";
import { ATTRIBUTES } from "./CardView";

/** A card at full size, and what the printed card cannot say. */
export function CardDetail({ card }: { card: Card }) {
  const { art } = useUi();
  const src = card.kind === "Agenda" ? art.agenda(card.name) : art.card(card.name);
  const courtier = card.kind === "Courtier";
  return (
    <div className="detail">
      {src ? <img className="detail-image" src={src} alt={card.name} /> : <h3>{card.name}</h3>}
      {courtier && (
        <dl className="live-attrs">
          {ATTRIBUTES.map((a) => (
            <div key={a} className={card.changed?.includes(a) ? "changed" : ""}>
              <dt>{a === "family" ? "house" : a}</dt>
              <dd>
                {card[a] as string}
                {card.changed?.includes(a) && <small> changed in play</small>}
                {card.mutated?.includes(a) && <small> · its one mutation is spent</small>}
              </dd>
            </div>
          ))}
        </dl>
      )}
      {card.defense && <p className="defense-note">Protected by {card.defense.name}.</p>}
    </div>
  );
}

export function Inspect({ card, onClose }: { card: Card | null; onClose(): void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = dialog.current;
    if (!d) return;
    if (card && !d.open) d.showModal();
    if (!card && d.open) d.close();
  }, [card]);
  return (
    <dialog
      ref={dialog}
      className="inspect"
      onClose={onClose}
      onClick={(e) => e.target === dialog.current && onClose()}
      aria-label={card ? card.name : "Card"}
    >
      {card && <CardDetail card={card} />}
      <button type="button" className="close" onClick={onClose}>
        Close
      </button>
    </dialog>
  );
}
