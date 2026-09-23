// A bot's hand, seen: a circle in the bot's colour travels from the hand on
// its chip to whatever it just played on -- a courtier it targeted, the seat
// a courtier moved into, a player it aimed at, the card it put down -- with a
// line back to the chip, so a move is seen coming from somebody. Then it
// fades. Pure decoration over the page; nothing here can be clicked.

import type { Action } from "./protocol";

function reducedMotion(): boolean {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

function centre(el: Element): { x: number; y: number } {
  const r = el.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
}

/** Where the move landed: its target if it had one, else the card itself. */
function landing(action: Action): Element | null {
  const q = (selector: string) => document.querySelector(selector);
  if (action.target_player !== null) return q(`[data-player="${action.target_player}"]`);
  if (action.courtier !== null) {
    const courtier = q(`[data-uid="${action.courtier}"] > .face`);
    if (courtier) return courtier; // gone if the action killed them
  }
  if (action.card !== null) {
    const card = q(`[data-uid="${action.card}"] > .face`);
    if (card) return card;
  }
  return q(".discard-pile");
}

const HOLD = 260;
const FADE = 220;

/**
 * Show `actor`'s hand making `action`. Call after the new board is drawn but
 * before the cards start moving, so the landing is measured where the cards
 * end up rather than where they set off from.
 */
export function showHand(actor: number, action: Action, colour: string, duration: number) {
  if (duration <= 0 || reducedMotion()) return;
  const chip = document.querySelector(`[data-player="${actor}"]`);
  const from = chip?.querySelector("[data-hand]") ?? chip;
  const to = landing(action);
  if (!from || !to) return;
  const a = centre(from);
  const b = centre(to);
  const length = Math.hypot(b.x - a.x, b.y - a.y);
  if (length < 4) return;

  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("class", "hand-trail");
  svg.setAttribute("aria-hidden", "true");
  const line = document.createElementNS(ns, "line");
  line.setAttribute("x1", String(a.x));
  line.setAttribute("y1", String(a.y));
  line.setAttribute("x2", String(b.x));
  line.setAttribute("y2", String(b.y));
  line.setAttribute("stroke", colour);
  line.setAttribute("stroke-dasharray", `${length}`);
  svg.appendChild(line);

  const dot = document.createElement("div");
  dot.className = "hand-dot";
  dot.setAttribute("aria-hidden", "true");
  dot.style.setProperty("--hand", colour);
  dot.style.left = `${a.x}px`;
  dot.style.top = `${a.y}px`;

  document.body.append(svg, dot);
  const easing = "cubic-bezier(0.2, 0.7, 0.2, 1)";
  line.animate([{ strokeDashoffset: length }, { strokeDashoffset: 0 }], { duration, easing, fill: "forwards" });
  dot.animate(
    [
      { transform: "translate(-50%, -50%) scale(0.6)" },
      { transform: `translate(calc(-50% + ${b.x - a.x}px), calc(-50% + ${b.y - a.y}px)) scale(1)` },
    ],
    { duration, easing, fill: "forwards" },
  );
  // Landed: a pulse, a moment to read it, then gone.
  const out = { delay: duration + HOLD, duration: FADE, fill: "forwards" as const };
  const fade = svg.animate([{ opacity: 1 }, { opacity: 0 }], out);
  dot.animate([{ opacity: 1 }, { opacity: 0 }], out);
  dot.animate(
    [{ boxShadow: `0 0 0 0 ${colour}` }, { boxShadow: `0 0 0 14px transparent` }],
    { delay: duration, duration: HOLD + FADE },
  );
  fade.finished.finally(() => {
    svg.remove();
    dot.remove();
  });
}
