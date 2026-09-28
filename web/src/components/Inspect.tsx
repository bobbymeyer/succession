import { useEffect, useRef, useState } from "react";
import type { Card } from "../protocol";
import { useUi } from "../art";
import { attributeText, GRID } from "./CardView";
import { Sigil, sigilLabel } from "./Sigil";

/** A card at full size, and what the printed card cannot say. */
export function CardDetail({ card }: { card: Card }) {
  const { art } = useUi();
  const src = card.kind === "Agenda" ? art.agenda(card.name) : art.card(card.name);
  const courtier = card.kind === "Courtier";
  return (
    <div className="detail">
      {src ? <img className="detail-image" src={src} alt={card.name} /> : <h3>{card.name}</h3>}
      {courtier && (
        <div className="live-sigil">
          <Sigil card={card} className="sigil big" />
          <span>{sigilLabel(card)}</span>
        </div>
      )}
      {courtier && (
        <dl className="live-attrs">
          {GRID.map(({ attribute: a, label }) => (
            <div key={a} className={card.changed?.includes(a) ? "changed" : ""}>
              <dt>{label}</dt>
              <dd>
                {attributeText(card, a)}
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

/** A neighbour in the hand, small and dim beside the card being looked at. */
function Peek({ card, side, onClick }: { card: Card; side: "prev" | "next"; onClick(): void }) {
  const { art } = useUi();
  const src = art.card(card.name);
  return (
    <button type="button" className={`peek ${side}`} onClick={onClick} tabIndex={-1} aria-hidden="true">
      {src ? <img src={src} alt="" draggable={false} /> : <span className="text-face">{card.name}</span>}
    </button>
  );
}

const Chevron = ({ flip }: { flip?: boolean }) => (
  <svg viewBox="0 0 16 16" aria-hidden="true" style={flip ? { transform: "scaleX(-1)" } : undefined}>
    <path d="M10 3 5 8l5 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

/**
 * A card at full size. A card from your hand pages through the rest of the
 * hand, round and round, by the arrows either side or the arrow keys.
 */
export function Inspect({
  card,
  hand,
  onPick,
  onClose,
}: {
  card: Card | null;
  hand: Card[];
  onPick(card: Card): void;
  onClose(): void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [from, setFrom] = useState<"left" | "right" | null>(null);
  useEffect(() => {
    const d = dialog.current;
    if (!d) return;
    if (card && !d.open) d.showModal();
    if (!card && d.open) d.close();
    if (!card) setFrom(null);
  }, [card]);

  const at = card ? hand.findIndex((c) => c.uid === card.uid) : -1;
  const n = at >= 0 && hand.length > 1 ? hand.length : 0;
  const shown = at >= 0 ? hand[at] : card;
  useEffect(() => {
    if (n) document.querySelector(`.mine [data-uid="${shown!.uid}"]`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [n, shown?.uid]);
  const go = (step: 1 | -1) => {
    if (!n) return;
    setFrom(step > 0 ? "right" : "left");
    onPick(hand[(at + step + n) % n]);
  };

  return (
    <dialog
      ref={dialog}
      className={`inspect${n ? " carousel" : ""}`}
      onClose={onClose}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      onKeyDown={(e) => {
        if (e.key === "ArrowRight") go(1);
        else if (e.key === "ArrowLeft") go(-1);
        else return;
        e.preventDefault();
      }}
      aria-label={shown ? shown.name : "Card"}
    >
      {shown && (
        <div className="stage" onClick={(e) => e.target === e.currentTarget && onClose()}>
          {n > 0 && (
            <>
              <button type="button" className="nav prev" onClick={() => go(-1)} aria-label="Previous card in your hand">
                <Chevron />
              </button>
              <Peek key={`p${hand[(at - 1 + n) % n].uid}`} card={hand[(at - 1 + n) % n]} side="prev" onClick={() => go(-1)} />
            </>
          )}
          <div key={shown.uid} className={`panel${from ? ` from-${from}` : ""}`}>
            <CardDetail card={shown} />
            {n > 0 && (
              <p className="count" aria-live="polite">
                {at + 1} of {n} in your hand
              </p>
            )}
          </div>
          {n > 0 && (
            <>
              <Peek key={`n${hand[(at + 1) % n].uid}`} card={hand[(at + 1) % n]} side="next" onClick={() => go(1)} />
              <button type="button" className="nav next" onClick={() => go(1)} aria-label="Next card in your hand">
                <Chevron flip />
              </button>
            </>
          )}
        </div>
      )}
      <button type="button" className="close" onClick={onClose}>
        Close
      </button>
    </dialog>
  );
}
