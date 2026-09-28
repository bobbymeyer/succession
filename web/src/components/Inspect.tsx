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
  moves,
  onPick,
  onClose,
}: {
  card: Card | null;
  hand: Card[];
  /** Play, discard and the like, for the card on show. */
  moves(uid: number): { label: string; run(): void }[];
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
  const offers = shown ? moves(shown.uid) : [];
  // The moves pop up over the card it was asked on, and go when you page on.
  const [askedOn, setAskedOn] = useState<number | null>(null);
  const asking = offers.length > 0 && askedOn === shown?.uid;
  const toggle = () => offers.length && setAskedOn(asking ? null : shown!.uid);
  // A focused move that goes away would take the arrow keys with it.
  useEffect(() => {
    const d = dialog.current;
    if (d?.open && !d.contains(document.activeElement)) d.focus();
  }, [asking, shown?.uid]);
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
      tabIndex={-1}
      onClose={onClose}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      onKeyDown={(e) => {
        if (e.key === "ArrowRight") go(1);
        else if (e.key === "ArrowLeft") go(-1);
        // Enter on a move plays it; anywhere else it brings the moves up.
        else if (e.key === "Enter" && offers.length && !(e.target as HTMLElement).closest(".moves")) toggle();
        else if (e.key === "Escape" && asking) setAskedOn(null);
        else if ((e.key === "ArrowDown" || e.key === "ArrowUp") && asking) {
          const buttons = [...e.currentTarget.querySelectorAll<HTMLButtonElement>(".moves button")];
          const i = buttons.indexOf(document.activeElement as HTMLButtonElement);
          buttons[(i + (e.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length]?.focus();
        }
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
            <div className={`playable${offers.length ? " can" : ""}${asking ? " asking" : ""}`} onClick={toggle}>
              <CardDetail card={shown} />
              {asking && (
                <div className="moves" role="group" aria-label={`What to do with ${shown.name}`} onClick={(e) => e.stopPropagation()}>
                  {offers.map((o, i) => (
                    <button
                      key={o.label}
                      type="button"
                      className={i === 0 ? "primary" : undefined}
                      data-testid="inspect-move"
                      autoFocus={i === 0}
                      onClick={o.run}
                    >
                      {o.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {(n > 0 || offers.length > 0) && (
              <p className="count" aria-live="polite">
                {n > 0 && `${at + 1} of ${n} in your hand`}
                {offers.length > 0 && (
                  <span className="keys">
                    {n > 0 && " · "}
                    {asking ? "Esc to close" : "Click or Enter to play"}
                  </span>
                )}
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
