// Building your move by hand: click a card to pick it up, then what it
// targets; or drag it where it goes. The same for a choice an event forces
// (a card to discard, a courtier to name). What is lit, what a click does and
// the instruction line all come from here.

import { useEffect, useState } from "react";
import { Offers, type Offer } from "./components/Offers";
import { NO_INTERACTION, type Interaction } from "./components/Board";
import type { Flow } from "./flow";
import { hintFor, pickHint } from "./hints";
import { type Selection } from "./moves";
import { visibleCards } from "./names";
import { discarding, drops, settled, stage, untargeted, type Stage } from "./play";
import type { Action, View } from "./protocol";
import type { Dragging } from "./useDrag";

export interface Play {
  /** How the table answers clicks and drags right now. */
  act: Interaction;
  /** Where the move being built stands; null when it is not your move. */
  now: Stage | null;
  /** The instruction line, for a mouse. */
  hint: string;
  /** Moves that win you the game now. */
  winning: Action[];
  answer(action: Action): void;
  /** Answer a choice an event forced, or a block, by card uid. */
  pick(uid: number): void;
  /** What can be done with a card from the inspector. */
  movesFor(uid: number): Offer[];
  /** A card is picked up (on a phone its choices sit in the dock). */
  holding: boolean;
  /** The picked-up card's choices. */
  offers: Offer[] | null;
  putDown(): void;
}

export function usePlay(
  flow: Flow,
  view: View | null,
  send: (choice: number) => void,
  drag: Dragging,
  /** Close the inspector before a move made from it. */
  closeInspector: () => void,
): { play: Play; reset(): void } {
  const [selection, setSelection] = useState<Selection>({});
  const [picked, setPicked] = useState<number | null>(null);
  const reset = () => {
    setSelection({});
    setPicked(null);
  };

  // Escape puts down whatever is picked up.
  useEffect(() => {
    const key = (e: KeyboardEvent) => e.key === "Escape" && reset();
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);

  const { turn, pick: pickPrompt } = flow;
  const actions = turn?.options ?? [];
  const now: Stage | null = turn ? stage(actions, selection) : null;
  const answer = (action: Action) => send(action.index);
  const pick = (uid: number) => send(uid);
  const pickVerb = pickPrompt?.kind === "courtier" ? "Name to die" : "Discard";

  /** Take a selection: play it if it pins one move down, else wait for more. */
  const apply = (next: Selection) => {
    const action = settled(actions, next);
    if (action) answer(action);
    else setSelection(next);
  };

  const movesFor = (uid: number): Offer[] => {
    const close = (run: () => void) => () => {
      closeInspector();
      run();
    };
    if (pickPrompt) return pickPrompt.options.some((c) => c.uid === uid) ? [{ label: pickVerb, run: close(() => pick(uid)) }] : [];
    if (!turn) return [];
    const out: Offer[] = [];
    const play = untargeted(actions, uid);
    if (play) out.push({ label: "Play", run: close(() => apply(play)) });
    if (actions.some((a) => a.card === uid && a.kind === "play" && (a.courtier !== null || a.target_player !== null))) {
      out.push({ label: "Choose a target", run: close(() => setSelection({ card: uid })) });
    }
    const discard = discarding(actions, uid);
    if (discard) out.push({ label: "Discard & Draw", run: close(() => apply(discard)) });
    return out;
  };

  /** Where a card may be dragged, and what dropping it there does. */
  const targetsFor = (uid: number): Map<string, () => void> => {
    const out = new Map<string, () => void>();
    if (turn && (now?.active === null || now?.active === uid)) {
      for (const [key, sel] of drops(actions, uid)) out.set(key, () => apply(sel));
    } else if (pickPrompt?.kind === "discard" && pickPrompt.options.some((c) => c.uid === uid)) {
      out.set("discard", () => pick(uid));
    }
    return out;
  };
  const onPress = (uid: number, e: React.PointerEvent<HTMLElement>) => drag.press(uid, e, targetsFor(uid));

  let act: Interaction = NO_INTERACTION;
  if (turn && now) {
    act = {
      cardLive: (uid) => now.cards.has(uid),
      cardSelected: (uid) => now.active === uid,
      onCard: (uid) => {
        if (drag.justDragged()) return;
        const next = now.cards.get(uid);
        if (next) apply(next);
      },
      seatLive: (seat) => now.seats.has(seat),
      seatSelected: (seat) => selection.seat === seat,
      onSeat: (seat) => {
        const next = now.seats.get(seat);
        if (next) apply(next);
      },
      playerLive: (p) => now.players.has(p),
      onPlayer: (p) => {
        const next = now.players.get(p);
        if (next) apply(next);
      },
      canDrag: (uid) => (now.active === null || now.active === uid) && drops(actions, uid).size > 0,
      onPress,
      dropLive: drag.dropLive,
      popover: (uid) =>
        uid === now.active && now.offers.length ? (
          <Offers offers={now.offers.map((o) => ({ label: o.label, run: () => apply(o.selection) }))} />
        ) : null,
    };
  } else if (pickPrompt) {
    const uids = pickPrompt.options.map((c) => c.uid);
    act = {
      ...NO_INTERACTION,
      cardLive: (uid) => uids.includes(uid),
      cardSelected: (uid) => picked === uid,
      onCard: (uid) => !drag.justDragged() && setPicked(picked === uid ? null : uid),
      canDrag: (uid) => pickPrompt.kind === "discard" && uids.includes(uid),
      onPress,
      dropLive: drag.dropLive,
      popover: (uid) => (uid === picked ? <Offers offers={[{ label: pickVerb, run: () => pick(uid) }]} /> : null),
    };
  }

  const hint = now && view ? hintFor(now, view, visibleCards(view)) : pickPrompt ? pickHint(pickPrompt) : "";
  const offers =
    turn && now && now.active !== null && now.offers.length
      ? now.offers.map((o) => ({ label: o.label, run: () => apply(o.selection) }))
      : pickPrompt && picked !== null
        ? [{ label: pickVerb, run: () => pick(picked) }]
        : null;

  return {
    play: {
      act,
      now,
      hint,
      winning: actions.filter((a) => a.wins),
      answer,
      pick,
      movesFor,
      holding: Boolean((turn && now?.active != null) || (pickPrompt && picked !== null)),
      offers,
      putDown: reset,
    },
    reset,
  };
}
