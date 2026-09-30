// What the table is waiting on, as pure logic (src/flow.ts).
import { expect, test } from "@playwright/test";
import { flowOf, type FlowInput } from "../src/flow";
import type { Card, EventReport, Prompt, Result, Update, View } from "../src/protocol";

const card = (uid: number, name = `Card ${uid}`): Card => ({ uid, name, kind: "Event" }) as Card;
const view = (turn = 3): View => ({ you: 0, turn }) as View;
const update = (prompt: Prompt | null, fields: Partial<Update> = {}): Update =>
  ({ seat: 0, view: view(), log: [], actor: 1, action: null, events: [], coach: null, prompt, result: null, ...fields }) as Update;

const TURN: Prompt = { kind: "turn", player: 0, options: [], card: null, summary: "", over: 0 };
const LIMIT: Prompt = { kind: "discard", player: 0, options: [card(4)], card: null, summary: "", over: 1 };
const DEBASEMENT: Prompt = { kind: "discard", player: 0, options: [card(4)], card: card(9, "Debasement"), summary: "", over: 0 };
const BLOCK: Prompt = { kind: "block", player: 0, options: [card(5)], card: card(6), about: card(7), attacker: 1, summary: "", over: 0 };
const REPORT = { card: card(9, "Caravan") } as EventReport;
const RESULT = { winners: [1], timeout: false, turns: 20 } as Result;

const input = (shown: Update | null, fields: Partial<FlowInput> = {}): FlowInput => ({
  shown,
  pending: 0,
  busy: false,
  briefing: false,
  events: null,
  limitNoted: null,
  ...fields,
});

test("with no game on screen, it is the title screen", () => {
  expect(flowOf(input(null)).phase).toBe("setup");
});

test("your move is live only once play has caught up", () => {
  expect(flowOf(input(update(TURN))).phase).toBe("turn");
  expect(flowOf(input(update(TURN))).turn).toBe(TURN);
  for (const behind of [{ pending: 2 }, { busy: true }]) {
    const flow = flowOf(input(update(TURN), behind));
    expect(flow.phase).toBe("watching");
    expect(flow.turn).toBeNull();
  }
});

test("a new deal waits on the briefing, whatever it would ask next", () => {
  expect(flowOf(input(update(null), { briefing: true, pending: 4 })).phase).toBe("briefing");
});

test("an event on screen holds the question behind it until it is read", () => {
  const shown = update(TURN);
  const flow = flowOf(input(shown, { events: { update: update(null, { events: [REPORT] }), left: 1 } }));
  expect(flow.phase).toBe("event");
  expect(flow.event).toBe(REPORT);
  expect(flow.turn).toBeNull();
});

test("an event's choice keeps the event in effect, even after yours is made", () => {
  const asking = flowOf(input(update(DEBASEMENT)));
  expect(asking.phase).toBe("pick");
  expect(asking.liveEvent).toBe(DEBASEMENT);
  // Answered: the engine is choosing for the others, and it is still in effect.
  const waiting = flowOf(input(update(DEBASEMENT), { busy: true }));
  expect(waiting.pick).toBeNull();
  expect(waiting.liveEvent).toBe(DEBASEMENT);
  // Its result is being read: the banner gives way.
  expect(flowOf(input(update(DEBASEMENT), { events: { update: update(null, { events: [REPORT] }), left: 1 } })).liveEvent).toBeNull();
});

test("a turn over the hand limit says so once, and is not an event", () => {
  const flow = flowOf(input(update(LIMIT)));
  expect(flow.phase).toBe("pick");
  expect(flow.limitNotice).toBe(true);
  expect(flow.liveEvent).toBeNull();
  expect(flowOf(input(update(LIMIT), { limitNoted: 3 })).limitNotice).toBe(false);
  // A new turn, a new notice.
  expect(flowOf(input(update(LIMIT, { view: view(7) }), { limitNoted: 3 })).limitNotice).toBe(true);
});

test("a rival's attack waits on your block", () => {
  const flow = flowOf(input(update(BLOCK)));
  expect(flow.phase).toBe("block");
  expect(flow.block).toBe(BLOCK);
  expect(flow.pick).toBeNull();
});

test("the game is over only when its last move has played out", () => {
  expect(flowOf(input(update(null, { result: RESULT }), { pending: 1 })).phase).toBe("watching");
  const flow = flowOf(input(update(null, { result: RESULT })));
  expect(flow.phase).toBe("over");
  expect(flow.over).toBe(RESULT);
});
