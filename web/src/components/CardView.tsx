import type { Attribute, Card } from "../protocol";
import { useUi } from "../art";

export type CardSize = "xxs" | "xs" | "sm" | "md" | "lg";

interface Props {
  card: Card;
  size?: CardSize;
  live?: boolean;
  selected?: boolean;
  onClick?: () => void;
  /** Courtiers: print the live attributes under the card. */
  caption?: boolean;
}

/** The grid every courtier's details keep, in play or in the inspector. */
export const GRID: { attribute: Attribute; label: string }[] = [
  { attribute: "estate", label: "Estate" },
  { attribute: "faith", label: "Faith" },
  { attribute: "family", label: "House" },
  { attribute: "origin", label: "Origin" },
];

/** What a cell shows: a barbarian's people ride along with their origin. */
export function attributeText(card: Card, attribute: Attribute): string {
  const value = card[attribute] as string;
  if (attribute === "origin" && card.people) return card.people;
  if (attribute === "family" && value === "None") return "No house";
  if (attribute === "faith" && value === "None") return "No faith";
  return value;
}

/**
 * A courtier's attributes as they stand now, always in the same places:
 *
 *   Estate | Faith
 *   House  | Origin (or people)
 *
 * Changed ones are marked.
 */
export function Attributes({ card }: { card: Card }) {
  return (
    <span className="attrs" role="list">
      {GRID.map(({ attribute, label }) => {
        const changed = card.changed?.includes(attribute);
        const text = attributeText(card, attribute);
        return (
          <span
            key={attribute}
            role="listitem"
            className={`attr attr-${attribute}${changed ? " changed" : ""}`}
            title={`${label}: ${card[attribute] as string}${changed ? " (changed in play)" : ""}`}
          >
            {text}
          </span>
        );
      })}
    </span>
  );
}

function Face({ card }: { card: Card }) {
  const { art } = useUi();
  const src = art.card(card.name);
  if (src) return <img src={src} alt={card.name} draggable={false} />;
  // No picture (the game rendition was not built): set the card in type.
  return (
    <span className="text-face">
      <span className="card-name">{card.name}</span>
      <span className="card-type">
        {card.kind}
        {card.estate ? ` · ${card.estate}` : ""}
      </span>
    </span>
  );
}

// One card on the table. Clicking a lit-up card makes a choice; clicking any
// other card picks it up to look at. The printed card shows printed
// attributes, so a courtier whose attributes changed in play says so on top.
export function CardView({ card, size = "md", live = false, selected = false, onClick, caption = false }: Props) {
  const { inspect, hover } = useUi();
  const courtier = card.kind === "Courtier";
  const changed = courtier && (card.changed?.length ?? 0) > 0;
  const classes = ["card", `size-${size}`];
  if (live) classes.push("live");
  if (selected) classes.push("selected");

  return (
    <div
      className={classes.join(" ")}
      data-uid={card.uid}
      onPointerEnter={(e) => e.pointerType === "mouse" && hover(card)}
      onPointerLeave={(e) => e.pointerType === "mouse" && hover(null)}
    >
      <button
        type="button"
        className="face"
        aria-pressed={live ? selected : undefined}
        aria-label={live ? `Choose ${card.name}` : `Look at ${card.name}`}
        onClick={live && onClick ? onClick : () => inspect(card)}
      >
        <Face card={card} />
        {changed && <span className="changed-flag">Changed</span>}
      </button>
      {live && (
        <button type="button" className="look" aria-label={`Look at ${card.name}`} onClick={() => inspect(card)}>
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <path d="M10.5 10.5 14 14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </button>
      )}
      {card.defense && (
        <button type="button" className="shield" onClick={() => inspect(card.defense!)} title="Look at the defense">
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M8 1.5 2.5 3.5v4c0 3.3 2.4 5.9 5.5 7 3.1-1.1 5.5-3.7 5.5-7v-4Z" fill="currentColor" />
          </svg>
          {card.defense.name}
        </button>
      )}
      {caption && courtier && <Attributes card={card} />}
    </div>
  );
}

/** The back of a card: someone's hand, the deck, a hidden agenda. */
export function CardBack({ size = "xs", label }: { size?: CardSize; label?: string }) {
  const { art } = useUi();
  return (
    <div className={`card back size-${size}`} aria-label={label} role={label ? "img" : undefined}>
      <span className="face">{art.back ? <img src={art.back} alt="" draggable={false} /> : <span className="text-face" />}</span>
    </div>
  );
}
