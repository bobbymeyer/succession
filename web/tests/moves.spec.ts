// The move builder is pure logic; test it without a browser.
import { expect, test } from "@playwright/test";
import { build, choose, clickCard } from "../src/moves";
import type { Action } from "../src/protocol";

let index = 0;
function action(fields: Partial<Action>): Action {
  return {
    index: index++,
    kind: "play",
    card: null,
    courtier: null,
    seat: null,
    target_player: null,
    sacrifice: null,
    value: null,
    text: "",
    ...fields,
  };
}

const PROMOTE_A = action({ card: 50, courtier: 1, seat: "Oracle" });
const PROMOTE_B = action({ card: 50, courtier: 2, seat: "Oracle" });
const PROMOTE_B2 = action({ card: 50, courtier: 2, seat: "Archpriest" });
const DISCARD = action({ kind: "discard", card: 50 });
const PLAY_COURTIER = action({ card: 7 });
const MOVE = action({ kind: "move", courtier: 3, seat: "Lord General" });
const PASS = action({ kind: "pass" });
const ACTIONS = [PROMOTE_A, PROMOTE_B, PROMOTE_B2, DISCARD, PLAY_COURTIER, MOVE, PASS];

test("a click on a hand card narrows to that card", () => {
  let b = build(ACTIONS, {});
  expect(b.field).toBe("card");
  b = build(ACTIONS, clickCard(ACTIONS, b, 50)!);
  expect(b.field).toBe("kind"); // play it or discard it
  b = build(ACTIONS, choose(b, "play"));
  expect(b.field).toBe("courtier");
  expect(b.choices).toEqual([1, 2]);
  b = build(ACTIONS, clickCard(ACTIONS, b, 2)!);
  expect(b.field).toBe("seat");
  b = build(ACTIONS, choose(b, "Archpriest"));
  expect(b.chosen).toBe(PROMOTE_B2);
});

test("a single remaining action needs no more choices", () => {
  const b = build(ACTIONS, clickCard(ACTIONS, build(ACTIONS, {}), 7)!);
  expect(b.chosen).toBe(PLAY_COURTIER);
});

test("a courtier in the outer circle starts a move", () => {
  const b = build(ACTIONS, clickCard(ACTIONS, build(ACTIONS, {}), 3)!);
  expect(b.chosen).toBe(MOVE);
});

test("a click on something that is not a choice does nothing", () => {
  const b = build(ACTIONS, {});
  expect(clickCard(ACTIONS, b, 99)).toBeNull();
  expect(clickCard(ACTIONS, b, 1)).toBeNull(); // a target, but no card chosen yet
});
