// Click-to-pick-up and drag-to-play, as pure logic.
import { expect, test } from "@playwright/test";
import { drops, settled, stage } from "../src/play";
import type { Action } from "../src/protocol";

let index = 0;
const act = (fields: Partial<Action>): Action => ({
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
});

// Hand: 50 Promotion (targets 1 into two seats), 7 a courtier, 60 Outmaneuver,
// 70 Adoption (target 1, pay with 7, value chosen). Outer courtier 3 can move.
const PROMOTE_ORACLE = act({ card: 50, courtier: 1, seat: "Oracle" });
const PROMOTE_ARCH = act({ card: 50, courtier: 1, seat: "Archpriest" });
const DISCARD_50 = act({ kind: "discard", card: 50 });
const PLAY_7 = act({ card: 7 });
const DISCARD_7 = act({ kind: "discard", card: 7 });
const OUTMANEUVER_2 = act({ card: 60, target_player: 2 });
const ADOPT = act({ card: 70, courtier: 1, sacrifice: 7, value: "Mitreas" });
const MOVE_3 = act({ kind: "move", courtier: 3, seat: "Lord General" });
const ACTIONS = [PROMOTE_ORACLE, PROMOTE_ARCH, DISCARD_50, PLAY_7, DISCARD_7, OUTMANEUVER_2, ADOPT, MOVE_3];

test("with nothing picked up, every card with a move is lit", () => {
  const s = stage(ACTIONS, {});
  expect(s.active).toBeNull();
  expect([...s.cards.keys()].sort((a, b) => a - b)).toEqual([3, 7, 50, 60, 70]);
  expect(s.cards.get(3)).toEqual({ card: null, kind: "move", courtier: 3 });
});

test("a picked-up courtier card offers Play and Discard & Draw above it", () => {
  const s = stage(ACTIONS, { card: 7 });
  expect(s.active).toBe(7);
  expect(s.offers.map((o) => o.label)).toEqual(["Play", "Discard & Draw"]);
  expect(settled(ACTIONS, s.offers[0].selection)).toBe(PLAY_7);
  expect(s.cards.get(7)).toEqual({}); // clicking it again puts it down
  expect(s.cards.get(50)).toEqual({ card: 50 }); // another card swaps the pick-up
});

test("a picked-up action lights its targets, then the seat it still needs", () => {
  const s = stage(ACTIONS, { card: 50 });
  expect(s.offers.map((o) => o.label)).toEqual(["Discard & Draw"]); // no untargeted play
  const onTarget = s.cards.get(1)!;
  expect(settled(ACTIONS, onTarget)).toBeNull();
  const next = stage(ACTIONS, onTarget);
  expect(next.step).toBe("seat");
  expect([...next.seats.keys()].sort()).toEqual(["Archpriest", "Oracle"]);
  expect(settled(ACTIONS, next.seats.get("Oracle")!)).toBe(PROMOTE_ORACLE);
});

test("an action aimed at a player lights that player", () => {
  const s = stage(ACTIONS, { card: 60 });
  expect(settled(ACTIONS, s.players.get(2)!)).toBe(OUTMANEUVER_2);
});

test("a single remaining choice settles the action at once", () => {
  // Adoption on courtier 1 has one payment and one value: pinned down.
  const s = stage(ACTIONS, { card: 70 });
  expect(settled(ACTIONS, s.cards.get(1)!)).toBe(ADOPT);
});

test("an outer courtier picked up lights the seats it can take", () => {
  const s = stage(ACTIONS, { card: null, kind: "move", courtier: 3 });
  expect(s.step).toBe("mover");
  expect(settled(ACTIONS, s.seats.get("Lord General")!)).toBe(MOVE_3);
});

test("dragging shows where each card can land", () => {
  expect([...drops(ACTIONS, 7).keys()].sort()).toEqual(["discard", "outer"]);
  expect([...drops(ACTIONS, 50).keys()].sort()).toEqual(["courtier:1", "discard"]);
  expect([...drops(ACTIONS, 60).keys()]).toEqual(["player:2"]);
  expect([...drops(ACTIONS, 3).keys()]).toEqual(["seat:Lord General"]);
  expect(settled(ACTIONS, drops(ACTIONS, 7).get("discard")!)).toBe(DISCARD_7);
});
