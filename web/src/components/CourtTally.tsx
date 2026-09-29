import type { ReactElement } from "react";
import type { View } from "../protocol";
import { HOUSE_COLOUR, ORIGIN_COLOUR } from "./Sigil";

// The court in the terms every agenda reads it: how many seats each house and
// each faith holds, and the barbarians. Counting captions on seven cards is
// arithmetic; this is the table at a glance. When any agenda is one courtier
// from complete, it says so -- which agenda, never whose, since the table
// shows totals and nothing a player holds.

const FAITH_SHAPE: Record<string, ReactElement> = {
  "The One God": <circle cx="10" cy="10" r="7.5" />,
  "Old Gods": <rect x="3" y="3" width="14" height="14" rx="1.5" />,
  "Mystery Cults": <polygon points="10,1.8 17.1,5.9 17.1,14.1 10,18.2 2.9,14.1 2.9,5.9" />,
};

function Icon({ children, fill, stroke }: { children: ReactElement; fill: string; stroke: string }) {
  return (
    <svg viewBox="0 0 20 20" className="tally-icon" aria-hidden="true" fill={fill} stroke={stroke} strokeWidth="2">
      {children}
    </svg>
  );
}

export function CourtTally({ view }: { view: View }) {
  const { court } = view;
  const mine = view.you >= 0 ? view.players[view.you].agenda : null;
  // Once the game is over there is nothing left to warn of.
  const close = view.over ? [] : court.close;
  const yours = close.find((a) => a.key === mine?.key);
  const others = close.filter((a) => a.key !== mine?.key);
  const item = (key: string, icon: ReactElement, count: number, label: string) => (
    <li key={key} className={count ? "" : "none"} title={label}>
      {icon}
      <span className="n">{count}</span>
      <span className="sr">{label}</span>
    </li>
  );

  return (
    <div className="tally" data-testid="court-tally">
      <ul aria-label="The court at a glance">
        <li className="seats" title="Seats filled">
          <span className="n">{`${court.filled}/7`}</span>
        </li>
        {Object.entries(court.houses).map(([house, n]) =>
          item(`h-${house}`, <Icon fill={HOUSE_COLOUR[house]} stroke="none"><circle cx="10" cy="10" r="7" /></Icon>, n, `House ${house}: ${n}`),
        )}
        {Object.entries(court.faiths).map(([faith, n]) =>
          item(`f-${faith}`, <Icon fill="none" stroke="currentColor">{FAITH_SHAPE[faith]}</Icon>, n, `${faith}: ${n}`),
        )}
        {item(
          "barbarians",
          <Icon fill={ORIGIN_COLOUR.Barbarian} stroke="none">
            {/* a war banner: no sigil uses the shape */}
            <path d="M4 2h2v16H4zM6 3h10l-3 3.5L16 10H6z" />
          </Icon>,
          court.barbarians,
          `Barbarians seated: ${court.barbarians}, ${court.barbarians_outside} more in the outer circle`,
        )}
      </ul>
      {yours && (
        <p className="tally-alert yours" data-testid="close-yours">
          ★ You are one courtier from {yours.name}.
        </p>
      )}
      {others.length > 0 && (
        <p className="tally-alert danger" data-testid="close-danger" role="status">
          ⚠ One courtier from victory: {others.map((a) => a.name).join(", ")}. If a rival holds {others.length > 1 ? "one" : "it"}, they win next.
        </p>
      )}
    </div>
  );
}
