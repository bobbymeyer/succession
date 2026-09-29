import type { Action, Card, Prompt, View } from "../protocol";
import { CardView } from "./CardView";
import { playerName } from "../names";

// The line that says what is being asked, and the whole list of legal moves
// under it, folded away, for anyone who would rather pick from a list.
export function StatusPanel({
  hint,
  prompt,
  onAction,
  onPick,
  pass,
  winning = [],
}: {
  hint: string;
  prompt: Prompt | null;
  onAction(action: Action): void;
  onPick(uid: number): void;
  pass: Action | null;
  /** Moves that complete your agenda now. */
  winning?: Action[];
}) {
  return (
    <div className="prompt" aria-live="polite">
      {winning.length > 0 && (
        <div className="win-now" data-testid="win-now">
          <strong>★ You can win now.</strong>
          {winning.every((a) => a.blockable) && <small className="muted"> Unless a rival blocks it.</small>}
          <div className="buttons">
            {winning.map((a) => (
              <button key={a.index} type="button" className="primary" onClick={() => onAction(a)}>
                {sentence(a.text)}
              </button>
            ))}
          </div>
        </div>
      )}
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

/** "move X -> Y" as a line a person would write. */
function sentence(text: string): string {
  const out = text.replace(/ -> /g, " into ");
  return out.charAt(0).toUpperCase() + out.slice(1);
}

// Someone attacks a seated courtier one of your Defenses covers: block it
// (both cards are thrown away and nothing happens), or let it land.
export function BlockPanel({
  view,
  prompt,
  onChoose,
}: {
  view: View;
  prompt: Prompt & { kind: "block" };
  onChoose(uid: number): void;
}) {
  return (
    <div className="prompt block-prompt" data-testid="block" aria-live="assertive">
      <p>
        <strong>{playerName(view, prompt.attacker)}</strong> plays <strong>{prompt.card.name}</strong> on{" "}
        <strong>{prompt.about.name}</strong>.
      </p>
      <p className="muted">You can block it: both cards are thrown away and nothing happens.</p>
      <div className="buttons">
        {prompt.options.map((c) => (
          <button key={c.uid} type="button" className="primary" data-testid="block-with" onClick={() => onChoose(c.uid)}>
            Block with {c.name}
          </button>
        ))}
        <button type="button" data-testid="let-it-land" onClick={() => onChoose(-1)}>
          Let it happen
        </button>
      </div>
    </div>
  );
}
