import type { Attribute, Card } from "../protocol";

const ATTRIBUTES: Attribute[] = ["estate", "faith", "family", "origin"];

interface Props {
  card: Card;
  live?: boolean;
  selected?: boolean;
  onClick?: () => void;
}

// A plain card: name, type line, and a courtier's live attributes. The card
// art replaces most of this in the next milestone; the attributes stay, since
// they change in play and the printed card cannot show that.
export function CardView({ card, live = false, selected = false, onClick }: Props) {
  const courtier = card.kind === "Courtier";
  const classes = ["card", `kind-${card.kind.toLowerCase()}`];
  if (live) classes.push("live");
  if (selected) classes.push("selected");
  const body = (
    <>
      <span className="card-name">{card.name}</span>
      {courtier ? (
        <span className="card-attrs">
          {ATTRIBUTES.map((a) => (
            <span key={a} className={card.changed?.includes(a) ? "attr changed" : "attr"} title={a}>
              {card[a] as string}
            </span>
          ))}
        </span>
      ) : (
        <span className="card-type">
          {card.kind}
          {card.estate ? ` · ${card.estate}` : ""}
        </span>
      )}
      {card.defense && <span className="card-defense">Shielded: {card.defense.name}</span>}
    </>
  );
  if (!onClick || !live) {
    return <div className={classes.join(" ")}>{body}</div>;
  }
  return (
    <button type="button" className={classes.join(" ")} onClick={onClick} aria-pressed={selected}>
      {body}
    </button>
  );
}
