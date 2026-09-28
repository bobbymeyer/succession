import type { Card } from "../protocol";

// A courtier's four attributes as one mark, read at a glance and at any size:
//
//   faith  -> the shape    One God a circle, Old Gods a square, Mystery Cults
//                          a hexagon; no faith a diamond (dashed when an
//                          Excommunication has emptied the slot)
//   house  -> its colour   Argaian red, Mitreas green, Amonides blue; no
//                          house black
//   estate -> the glyph    Military a sword, Merchant a coin, Church praying
//                          hands; Commons nothing
//   origin -> the border   Imperial gold, Barbarian iron
//
// It always shows the attributes as they stand now, so a courtier changed in
// play wears their new sigil while the printed card keeps the old words.

export const HOUSE_COLOUR: Record<string, string> = {
  Argaian: "#c8453a",
  Mitreas: "#3f9a55",
  Amonides: "#3d6fc4",
  None: "#15171c",
};
export const ORIGIN_COLOUR: Record<string, string> = {
  Imperial: "#f0c865",
  Barbarian: "#aeb8c4",
};
const GLYPH_INK = "#f5ecd8";

const HEX = "20,2.5 35.2,11.25 35.2,28.75 20,37.5 4.8,28.75 4.8,11.25";
const DIAMOND = "20,1.5 38.5,20 20,38.5 1.5,20";

function Shape({ faith, ...paint }: { faith: string } & React.SVGProps<SVGElement>) {
  const p = paint as React.SVGProps<SVGCircleElement & SVGRectElement & SVGPolygonElement>;
  switch (faith) {
    case "The One God":
      return <circle cx="20" cy="20" r="16.5" {...p} />;
    case "Old Gods":
      return <rect x="4.5" y="4.5" width="31" height="31" rx="3" {...p} />;
    case "Mystery Cults":
      return <polygon points={HEX} {...p} />;
    default:
      return <polygon points={DIAMOND} {...p} />;
  }
}

function Glyph({ estate, ground }: { estate: string; ground: string }) {
  switch (estate) {
    case "Military":
      return (
        <g fill={GLYPH_INK}>
          <path d="M20 7.5 22.6 11.5V24h-5.2V11.5Z" />
          <rect x="13" y="24" width="14" height="2.8" rx="1" />
          <rect x="18.7" y="26.8" width="2.6" height="4.6" />
          <circle cx="20" cy="32.6" r="2" />
        </g>
      );
    case "Merchant":
      return (
        <g>
          <circle cx="20" cy="20" r="9" fill={GLYPH_INK} />
          <circle cx="20" cy="20" r="6.2" fill="none" stroke={ground} strokeWidth="1.4" />
          <rect x="18.2" y="18.2" width="3.6" height="3.6" fill={ground} />
        </g>
      );
    case "Church":
      // Two palms pressed together: broad, pointed, split down the middle.
      return (
        <g>
          <path
            d="M20 6.5C17.2 9.2 14.8 13.4 14.3 18.5L13.8 23.2 12.2 25.8V31.5h15.6v-5.7l-1.6-2.6-.5-4.7C25.2 13.4 22.8 9.2 20 6.5Z"
            fill={GLYPH_INK}
          />
          <path d="M20 9.5v22M12.2 26.4h15.6" stroke={ground} strokeWidth="1.5" />
        </g>
      );
    default:
      return null; // Commons
  }
}

/** Read aloud: "Mitreas, Merchant, Mystery Cults, Imperial". */
export function sigilLabel(card: Pick<Card, "estate" | "faith" | "family" | "origin">): string {
  const house = card.family && card.family !== "None" ? card.family : "No house";
  const faith = !card.faith || card.faith === "None" ? "No faith" : card.faith;
  return `${house}, ${card.estate ?? "no estate"}, ${faith}, ${card.origin ?? ""}`.replace(/, $/, "");
}

export function Sigil({
  card,
  className = "sigil",
}: {
  card: Pick<Card, "estate" | "faith" | "family" | "origin">;
  className?: string;
}) {
  const fill = HOUSE_COLOUR[card.family ?? "None"] ?? HOUSE_COLOUR.None;
  const ring = ORIGIN_COLOUR[card.origin ?? "Imperial"] ?? ORIGIN_COLOUR.Imperial;
  const faith = card.faith ?? "None";
  const label = sigilLabel(card);
  return (
    <svg className={className} viewBox="0 0 40 40" role="img" aria-label={label}>
      <title>{label}</title>
      {/* A dark edge first, so the mark stands off any painting. */}
      <Shape faith={faith} fill="none" stroke="rgba(0,0,0,0.65)" strokeWidth={6.5} strokeLinejoin="round" />
      <Shape
        faith={faith}
        fill={fill}
        stroke={ring}
        strokeWidth={3.2}
        strokeLinejoin="round"
        strokeDasharray={faith === "None" ? "5 3.2" : undefined}
      />
      <Glyph estate={card.estate ?? ""} ground={fill} />
    </svg>
  );
}

// How to read one, for the rules: each attribute on its own.
export function SigilKey() {
  const plain = { estate: "Commons", faith: "The One God", family: "None", origin: "Imperial" };
  const rows: { title: string; items: [string, Partial<typeof plain>][] }[] = [
    {
      title: "Faith is the shape",
      items: [
        ["The One God", { faith: "The One God" }],
        ["Old Gods", { faith: "Old Gods" }],
        ["Mystery Cults", { faith: "Mystery Cults" }],
        ["Godless", { faith: "Godless" }],
        ["No faith (excommunicated)", { faith: "None" }],
      ],
    },
    {
      title: "House is the colour",
      items: [
        ["Argaian", { family: "Argaian" }],
        ["Mitreas", { family: "Mitreas" }],
        ["Amonides", { family: "Amonides" }],
        ["No house", { family: "None" }],
      ],
    },
    {
      title: "Estate is the sign",
      items: [
        ["Military", { estate: "Military" }],
        ["Merchant", { estate: "Merchant" }],
        ["Church", { estate: "Church" }],
        ["Commons", { estate: "Commons" }],
      ],
    },
    {
      title: "Origin is the border",
      items: [
        ["Imperial", { origin: "Imperial" }],
        ["Barbarian", { origin: "Barbarian" }],
      ],
    },
  ];
  return (
    <div className="sigil-key">
      {rows.map((row) => (
        <div key={row.title}>
          <h4>{row.title}</h4>
          <ul>
            {row.items.map(([name, part]) => (
              <li key={name}>
                <Sigil card={{ ...plain, ...part }} />
                <span>{name}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
