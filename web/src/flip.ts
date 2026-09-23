// Cards moving between zones, done the FLIP way: note where every card is
// (First), let React draw the next board (Last), then play each card from
// where it was to where it is now (Invert, Play). Cards are matched by uid,
// so a courtier leaving your hand for the outer circle, or a seat for the
// discard, glides across the table even though React drew it afresh. A card
// that was nowhere visible -- it came out of a bot's hand -- flies in from
// the hand on that player's chip, growing from the size of the card back
// there to its size on the table.

interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Snapshot {
  cards: Map<number, Box>;
  players: Map<number, Box>;
}

export const EMPTY: Snapshot = { cards: new Map(), players: new Map() };

function box(el: Element): Box {
  const r = el.getBoundingClientRect();
  // Page coordinates, so scrolling between two updates is not a move.
  return { x: r.left + window.scrollX, y: r.top + window.scrollY, w: r.width, h: r.height };
}

export function measure(): Snapshot {
  const cards = new Map<number, Box>();
  const players = new Map<number, Box>();
  document.querySelectorAll<HTMLElement>("[data-uid]").forEach((el) => cards.set(Number(el.dataset.uid), box(el)));
  // A player's hand where there is one on show, else their place at the table.
  document.querySelectorAll<HTMLElement>("[data-player]").forEach((el) => {
    const hand = el.querySelector("[data-hand]");
    players.set(Number(el.dataset.player), box(hand ?? el));
  });
  return { cards, players };
}

const EASE = "cubic-bezier(0.2, 0.7, 0.2, 1)";
const GLOW = "0 0 0 3px rgba(240, 200, 101, 0.95), 0 0 24px rgba(240, 200, 101, 0.8)";

function reducedMotion(): boolean {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

/** Play every card from where `before` saw it to where it is now. */
export function play(before: Snapshot, actor: number, you: number, duration: number) {
  if (duration <= 0 || reducedMotion()) return;
  const source = actor >= 0 && actor !== you ? before.players.get(actor) : undefined;

  document.querySelectorAll<HTMLElement>("[data-uid]").forEach((el) => {
    const uid = Number(el.dataset.uid);
    const now = box(el);
    const was = before.cards.get(uid);
    let from: Keyframe | null = null;

    if (was) {
      const dx = was.x - now.x;
      const dy = was.y - now.y;
      const scale = now.w ? was.w / now.w : 1;
      if (Math.abs(dx) < 2 && Math.abs(dy) < 2 && Math.abs(scale - 1) < 0.02) return; // stayed put
      from = { transform: `translate(${dx}px, ${dy}px) scale(${scale})` };
    } else if (source && before.cards.size) {
      // Out of a bot's hand: from the card back on their chip, at its size.
      const dx = source.x + source.w / 2 - (now.x + now.w / 2);
      const dy = source.y + source.h / 2 - (now.y + now.h / 2);
      const scale = Math.max(0.12, Math.min(1, source.w / (now.w || 1)));
      from = { transform: `translate(${dx}px, ${dy}px) scale(${scale})`, opacity: 0.4 };
    } else {
      from = { transform: "translateY(10px)", opacity: 0 };
    }

    el.style.transformOrigin = was ? "0 0" : "50% 50%";
    el.animate([from, { transform: "none", opacity: 1 }], { duration, easing: EASE });
    // A lingering glow says which card just moved, after it lands.
    el.querySelector(".face")?.animate(
      [{ boxShadow: GLOW }, { boxShadow: GLOW, offset: 0.4 }, {}],
      { duration: duration * 3, easing: "ease-out" },
    );
  });
}
