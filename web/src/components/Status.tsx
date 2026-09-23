import type { Action, Card, Prompt, View } from "../protocol";
import { CardView } from "./CardView";

// The line that says what is being asked, and the whole list of legal moves
// under it, folded away, for anyone who would rather pick from a list.
export function StatusPanel({
  hint,
  prompt,
  onAction,
  onPick,
  pass,
}: {
  hint: string;
  prompt: Prompt | null;
  onAction(action: Action): void;
  onPick(uid: number): void;
  pass: Action | null;
}) {
  return (
    <div className="prompt" aria-live="polite">
      <p>{hint}</p>
      {pass && (
        <div className="buttons">
          <button type="button" onClick={() => onAction(pass)}>
            Pass
          </button>
        </div>
      )}
      {prompt?.kind === "turn" && (
        <details className="all-moves">
          <summary>All {prompt.options.length} legal moves</summary>
          <ul>
            {prompt.options.map((a) => (
              <li key={a.index}>
                <button type="button" className="link" data-testid="move-option" onClick={() => onAction(a)}>
                  {a.text}
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}
      {prompt && prompt.kind !== "turn" && (
        <details className="all-moves">
          <summary>Choose from a list</summary>
          <ul>
            {prompt.options.map((c: Card) => (
              <li key={c.uid}>
                <button type="button" className="link" data-testid="pick-option" onClick={() => onPick(c.uid)}>
                  {c.name}
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

// Face up, at a readable size, where a played action lands: the last card
// thrown away, and a place to drop the next one.
export function DiscardPile({ view, dropLive }: { view: View; dropLive: boolean }) {
  return (
    <section className={`discard-pile${dropLive ? " drop-live" : ""}`} data-drop="discard" aria-label="Discard pile">
      <div className="pile-card">
        {view.discard_top ? (
          <CardView card={view.discard_top} size="md" />
        ) : (
          <div className="card size-md empty-slot" />
        )}
      </div>
      <div className="pile-text">
        <h2>Discard pile</h2>
        <span>
          {view.discard} {view.discard === 1 ? "card" : "cards"}
        </span>
        {dropLive && <strong className="drop-hint">Drop to discard</strong>}
      </div>
    </section>
  );
}
