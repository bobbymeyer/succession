import type { Action, Card, Prompt, View } from "../protocol";
import { type Builder, type Field, type Value } from "../moves";
import { playerName } from "../names";

interface TurnProps {
  view: View;
  prompt: Extract<Prompt, { kind: "turn" }>;
  builder: Builder;
  cards: Map<number, Card>;
  onChoose(value: Value): void;
  onSelectAction(action: Action): void;
  onConfirm(): void;
  onReset(): void;
}

const ASK: Record<Field, string> = {
  card: "Your move. Pick a card from your hand, or a courtier in the outer circle to seat.",
  kind: "Play it or discard it?",
  courtier: "Choose the courtier it targets.",
  seat: "Choose a seat.",
  target_player: "Choose a player.",
  sacrifice: "Choose a courtier from your hand to pay for it.",
  value: "Choose what they become.",
};

function label(field: Field, value: Value, view: View, cards: Map<number, Card>): string {
  if (value === null) return field === "card" ? "No card" : "None";
  if (field === "card" || field === "courtier" || field === "sacrifice") {
    return cards.get(value as number)?.name ?? `card ${value}`;
  }
  if (field === "target_player") return playerName(view, value as number);
  if (field === "kind") return { play: "Play it", discard: "Discard it", move: "Move", pass: "Pass" }[value as string] ?? String(value);
  return String(value);
}

export function TurnPanel({ view, prompt, builder, cards, onChoose, onSelectAction, onConfirm, onReset }: TurnProps) {
  const started = Object.keys(builder.selection).length > 0;
  const pass = prompt.options.find((a) => a.kind === "pass");
  // Board clicks cover cards and seats; everything else needs a button.
  const buttons = builder.field !== null && builder.field !== "card";

  return (
    <div className="prompt">
      {builder.chosen ? (
        <>
          <p>{builder.chosen.text}</p>
          <div className="buttons">
            <button type="button" className="primary" data-testid="confirm" onClick={onConfirm}>
              Confirm
            </button>
            <button type="button" onClick={onReset}>
              Back
            </button>
          </div>
        </>
      ) : (
        <>
          <p>{builder.field ? ASK[builder.field] : "No moves."}</p>
          {buttons && (
            <div className="buttons">
              {builder.choices.map((value) => (
                <button key={String(value)} type="button" onClick={() => onChoose(value)}>
                  {label(builder.field!, value, view, cards)}
                </button>
              ))}
            </div>
          )}
          <div className="buttons">
            {!started && pass && (
              <button type="button" onClick={() => onSelectAction(pass)}>
                Pass
              </button>
            )}
            {started && (
              <button type="button" onClick={onReset}>
                Back
              </button>
            )}
          </div>
        </>
      )}
      <details className="all-moves">
        <summary>
          {started ? `${builder.remaining.length} matching moves` : `All ${prompt.options.length} legal moves`}
        </summary>
        <ul>
          {builder.remaining.map((a) => (
            <li key={a.index}>
              <button type="button" className="link" data-testid="move-option" onClick={() => onSelectAction(a)}>
                {a.text}
              </button>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}

interface PickProps {
  prompt: Extract<Prompt, { kind: "courtier" | "discard" }>;
  picked: number | null;
  onPick(uid: number): void;
  onConfirm(): void;
}

export function PickPanel({ prompt, picked, onPick, onConfirm }: PickProps) {
  const ask =
    prompt.kind === "courtier"
      ? `${prompt.card.name}: every player names a courtier to die. Name yours.`
      : `${prompt.card.name}: every player discards. Choose a card to throw away.`;
  return (
    <div className="prompt">
      <p>{ask}</p>
      <div className="buttons">
        {prompt.options.map((c) => (
          <button
            key={c.uid}
            type="button"
            data-testid="pick-option"
            aria-pressed={picked === c.uid}
            className={picked === c.uid ? "selected" : ""}
            onClick={() => onPick(c.uid)}
          >
            {c.name}
          </button>
        ))}
      </div>
      {picked !== null && (
        <div className="buttons">
          <button type="button" className="primary" data-testid="confirm" onClick={onConfirm}>
            Confirm
          </button>
        </div>
      )}
    </div>
  );
}
