// Dragging a card from your hand to where it goes: the outer circle, a seat,
// a player, the discard pile. A mouse drags at once; a finger has to hold the
// card a moment first, so a swipe still scrolls the page.

import { useRef, useState } from "react";

/** How long a finger holds a card before it can be dragged. */
const DRAG_HOLD_MS = 200;

/** A card being dragged, from pointer-down until it is dropped. */
interface Drag {
  uid: number;
  source: HTMLElement;
  x0: number;
  y0: number;
  ghost: HTMLElement | null;
  targets: Map<string, () => void>;
}

export interface Dragging {
  /** Start watching a pointer pressed on a card, with what dropping it on each target does. */
  press(uid: number, e: React.PointerEvent<HTMLElement>, targets: Map<string, () => void>): void;
  /** Whether a drop target is lit, a card being over the table that can land there. */
  dropLive(key: string): boolean;
  /** A drag just ended: the click that follows it is not a click. */
  justDragged(): boolean;
}

export function useDrag(): Dragging {
  const [dropping, setDropping] = useState<Set<string>>(() => new Set());
  const dragging = useRef<Drag | null>(null);
  const justDragged = useRef(false);

  const press = (uid: number, e: React.PointerEvent<HTMLElement>, targets: Map<string, () => void>) => {
    if (e.button !== 0) return;
    if (!targets.size) return;
    const source = (e.currentTarget.closest(".card") as HTMLElement) ?? e.currentTarget;
    dragging.current = { uid, source, x0: e.clientX, y0: e.clientY, ghost: null, targets };
    // A finger has to hold a card a moment before it drags: until then a
    // swipe is the page scrolling, and the drag lets go. Once it is held, the
    // page stops scrolling under it.
    const touch = e.pointerType === "touch";
    let armed = !touch;
    const block = (tev: TouchEvent) => armed && tev.preventDefault();
    const arm = touch
      ? window.setTimeout(() => {
          armed = true;
          source.classList.add("armed");
          navigator.vibrate?.(8);
        }, DRAG_HOLD_MS)
      : 0;
    if (touch) document.addEventListener("touchmove", block, { passive: false });
    const release = () => {
      window.clearTimeout(arm);
      source.classList.remove("armed");
      document.removeEventListener("touchmove", block);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
    };
    const move = (ev: PointerEvent) => {
      const d = dragging.current;
      if (!d) return;
      if (!d.ghost) {
        if (Math.hypot(ev.clientX - d.x0, ev.clientY - d.y0) < 6) return; // still a click
        // Moved before the hold, or held into a look at the card: not a drag.
        if (!armed || document.querySelector("dialog[open]")) {
          release();
          dragging.current = null;
          return;
        }
        const rect = d.source.getBoundingClientRect();
        const ghost = d.source.cloneNode(true) as HTMLElement;
        ghost.classList.add("ghost");
        ghost.style.width = `${rect.width}px`;
        ghost.style.left = `${rect.left}px`;
        ghost.style.top = `${rect.top}px`;
        ghost.dataset.dx = String(d.x0 - rect.left);
        ghost.dataset.dy = String(d.y0 - rect.top);
        ghost.removeAttribute("data-uid");
        document.body.appendChild(ghost);
        d.ghost = ghost;
        d.source.classList.add("dragging");
        setDropping(new Set(d.targets.keys()));
      }
      d.ghost.style.left = `${ev.clientX - Number(d.ghost.dataset.dx)}px`;
      d.ghost.style.top = `${ev.clientY - Number(d.ghost.dataset.dy)}px`;
    };
    const up = (ev: PointerEvent) => {
      release();
      const d = dragging.current;
      dragging.current = null;
      if (!d?.ghost) return; // a click: the button's own click handler takes it
      d.ghost.remove();
      d.source.classList.remove("dragging");
      setDropping(new Set());
      justDragged.current = true;
      setTimeout(() => (justDragged.current = false), 0);
      const key = document.elementFromPoint(ev.clientX, ev.clientY)?.closest("[data-drop]")?.getAttribute("data-drop");
      if (key) d.targets.get(key)?.();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
  };

  return { press, dropLive: (key) => dropping.has(key), justDragged: () => justDragged.current };
}
