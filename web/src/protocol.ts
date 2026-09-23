// The shapes that cross from the Python engine (succession/webapi.py and
// succession/session.py) to the page. Python builds them; nothing here is
// computed from the rules.

export type Estate = "Military" | "Church" | "Merchant" | "Commons";
export type Attribute = "estate" | "faith" | "family" | "origin";

export interface Card {
  uid: number;
  name: string;
  kind: string; // "Courtier", "Promotion", "Event", ...
  estate: string | null;
  // Courtiers only: live attributes, which differ from the printed card, and
  // which have spent their one mutation.
  faith?: string;
  family?: string;
  origin?: string;
  changed?: Attribute[];
  mutated?: Attribute[];
  defense?: Card | null;
}

export interface Seat {
  seat: string;
  estate: Estate;
  courtier: Card | null;
}

export interface Clause {
  label: string;
  have: number;
  need: number;
  met: boolean;
  waiting: number | null; // helpful courtiers in the outer circle
}

export interface Agenda {
  key: string;
  name: string;
  met: boolean;
  status: Clause[];
}

export interface Player {
  seat: number;
  tier: string; // "human", "naive", "greedy", "strategic"
  hand: number;
  agenda: Agenda | null; // null while hidden
  skips_next_turn: boolean;
}

export interface View {
  you: number; // -1 for a spectator
  turn: number;
  current: number;
  over: boolean;
  winners: number[];
  players: Player[];
  hand: Card[];
  seats: Seat[];
  outer: Card[];
  deck: number;
  discard: number;
  discard_top: Card | null;
  removed: number;
  frozen: { inner: boolean; board: boolean };
}

export interface Action {
  index: number;
  kind: "play" | "move" | "discard" | "pass";
  card: number | null;
  courtier: number | null;
  seat: string | null;
  target_player: number | null;
  sacrifice: number | null;
  value: string | null;
  text: string;
}

export type Prompt =
  | { kind: "turn"; player: number; options: Action[]; card: null }
  | { kind: "courtier" | "discard"; player: number; options: Card[]; card: Card };

export interface GameRecord {
  version: number;
  seed: number;
  config: Record<string, unknown>;
  decisions: number[];
}

export interface Result {
  winners: number[];
  timeout: boolean;
  turns: number;
  record: GameRecord;
}

export interface Update {
  seat: number;
  view: View;
  log: string[];
  actor: number; // whose move this update shows; -1 before anyone's
  action: Action | null; // that move, all of it face up on the table
  prompt: Prompt | null;
  result: Result | null;
}

export interface TableOptions {
  player_types: string[];
  min_players: number;
  max_players: number;
}

// -- worker messages --------------------------------------------------------
export type Request =
  | { type: "new"; players: string[]; seed?: number }
  | { type: "answer"; choice: number }
  | { type: "load"; record: GameRecord }
  | { type: "export"; records: GameRecord[] };

/** The requests that play the game; each answers with updates. */
export type GameRequest = Exclude<Request, { type: "export" }>;

export type WorkerMessage =
  | { type: "ready"; options: TableOptions; python: string }
  | { type: "updates"; id: number; updates: Update[] }
  | { type: "text"; id: number; text: string }
  | { type: "error"; id: number | null; message: string };
