import { CourtTally } from "./CourtTally";
import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";
import type { Card, Player, View } from "../protocol";
import { useUi } from "../art";
import { playerName, seatColour, tierName } from "../names";
import { CardBack, CardView } from "./CardView";

export interface Interaction {
  cardLive(uid: number): boolean;
  cardSelected(uid: number): boolean;
  onCard(uid: number): void;
  seatLive(seat: string): boolean;
  seatSelected(seat: string): boolean;
  onSeat(seat: string): void;
  playerLive(seat: number): boolean;
  onPlayer(seat: number): void;
  /** Can this card be picked up and dragged? */
  canDrag(uid: number): boolean;
  onPress(uid: number, event: ReactPointerEvent<HTMLElement>): void;
  /** While a card is dragged: the places it may be dropped. */
  dropLive(key: string): boolean;
  /** Buttons over a picked-up card. */
  popover(uid: number): ReactNode;
}

export const NO_INTERACTION: Interaction = {
  cardLive: () => false,
  cardSelected: () => false,
  onCard: () => {},
  seatLive: () => false,
  seatSelected: () => false,
  onSeat: () => {},
  playerLive: () => false,
  onPlayer: () => {},
  canDrag: () => false,
  onPress: () => {},
  dropLive: () => false,
  popover: () => null,
};

/** A hidden agenda is a card back; a revealed one is the agenda card. */
function Agenda({ player, size }: { player: Player; size: "xxs" | "xs" | "sm" | "md" }) {
  const { art, inspect } = useUi();
  if (!player.agenda) return <CardBack size={size} label="Hidden agenda" />;
  const src = art.thumb(art.agenda(player.agenda.name));
  // An agenda is not a card in the engine's sense; show it as one to look at.
  const asCard: Card = { uid: -1, name: player.agenda.name, kind: "Agenda", estate: null };
  return (
    <button
      type="button"
      className={`card agenda-card size-${size}`}
      onClick={() => src && inspect(asCard)}
      aria-label={`Agenda: ${player.agenda.name}`}
    >
      <span className="face">
        {src ? <img src={src} alt={player.agenda.name} /> : <span className="text-face">{player.agenda.name}</span>}
      </span>
    </button>
  );
}

// A compact place at the table: who, how many cards, their agenda (a card
// back until it is revealed). The whole row stays one line high.
/** Your private guesses at rivals' hidden agendas, and how to change one. */
export interface Suspicions {
  agendas: string[]; // every agenda's name, to guess from
  guess: Record<number, string>; // seat -> agenda name
  onGuess(seat: number, agenda: string | null): void;
}

function Suspect({ seat, suspicions }: { seat: number; suspicions: Suspicions }) {
  const guess = suspicions.guess[seat];
  return (
    <label className={`suspect${guess ? " guessed" : ""}`} title="Your guess at their agenda: only you see it">
      <span className="sr">Your guess at their agenda</span>
      <select
        data-testid={`suspect-${seat}`}
        value={guess ?? ""}
        onChange={(e) => suspicions.onGuess(seat, e.target.value || null)}
        onClick={(e) => e.stopPropagation()}
      >
        <option value="">?</option>
        {suspicions.agendas.map((a) => (
          <option key={a} value={a}>
            {a}
          </option>
        ))}
      </select>
      <span className="suspect-face" aria-hidden="true">
        {guess ? shortAgenda(guess) : "?"}
      </span>
    </label>
  );
}

/** "Faith Ascendant: Old Gods" as "Old Gods?"; "Barbarian Conquest" as "Conquest?". */
function shortAgenda(name: string): string {
  const short = name.includes(":") ? name.split(":")[1].trim() : name.replace("Barbarian ", "");
  return `${short}?`;
}

function Opponent({
  view,
  player,
  act,
  turn,
  next,
  suspicions,
}: {
  view: View;
  player: Player;
  act: Interaction;
  turn: number | null;
  next: boolean;
  suspicions?: Suspicions;
}) {
  const classes = ["opponent"];
  if (player.seat === turn) classes.push("current");
  if (next) classes.push("next");
  if (view.winners.includes(player.seat)) classes.push("winner");
  const live = act.playerLive(player.seat);
  if (live) classes.push("live");
  if (act.dropLive(`player:${player.seat}`)) classes.push("drop-live");
  return (
    <div
      className={classes.join(" ")}
      style={{ "--seat": seatColour(player.seat) } as React.CSSProperties}
      data-player={player.seat}
      data-drop={`player:${player.seat}`}
      aria-label={playerName(view, player.seat)}
      role={live ? "button" : undefined}
      tabIndex={live ? 0 : undefined}
      onClick={live ? () => act.onPlayer(player.seat) : undefined}
      onKeyDown={live ? (e) => (e.key === "Enter" || e.key === " ") && act.onPlayer(player.seat) : undefined}
    >
      <span className="who">
        <span className="seat-dot" aria-hidden="true" />
        <strong>P{player.seat}</strong> <span className="tier">{tierName(player.tier).replace(" bot", "")}</span>
      </span>
      <span className="hand-count" data-hand={player.seat} title={`${player.hand} cards in hand`}>
        <CardBack size="xxs" />
        {player.hand}
      </span>
      <span className="their-agenda" title={player.agenda ? player.agenda.name : "Agenda hidden"}>
        {player.agenda ? (
          <>
            <Agenda player={player} size="xxs" />
            <span className="agenda-name">{player.agenda.name}</span>
          </>
        ) : suspicions ? (
          <Suspect seat={player.seat} suspicions={suspicions} />
        ) : (
          <span className="hidden-agenda" aria-label="Agenda hidden">
            ?
          </span>
        )}
      </span>
      {player.skips_next_turn && <span className="flag">Skips</span>}
      {next && <span className="next-tag">next</span>}
    </div>
  );
}

// `playing` is a bot whose card is still on its way to the table: until it
// lands, it is still that bot's turn as far as anyone watching can tell.
// `won` is the court that won the game, each courtier with its winner's
// colour; they light up and bounce once the game is over.
// Board courtiers are places to drop an action on; hand cards are not.
/** Cards to mark: those serving your agenda, and those in a move that wins it. */
export interface Marks {
  helps: Set<number>;
  wins: Set<number>;
}
const NO_MARKS: Marks = { helps: new Set(), wins: new Set() };

/** Your agenda's courtiers: seated for it, or able to be. */
export function marksFor(view: View, winning: Set<number> = new Set()): Marks {
  const agenda = view.you >= 0 && !view.over ? view.players[view.you].agenda : null;
  return { helps: new Set([...(agenda?.seated ?? []), ...(agenda?.helpers ?? [])]), wins: winning };
}

function cardFor(act: Interaction, c: Card, size: "sm" | "md" | "lg", onBoard = true, marks: Marks = NO_MARKS) {
  return (
    <CardView
      key={c.uid}
      helps={marks.helps.has(c.uid)}
      wins={marks.wins.has(c.uid)}
      card={c}
      size={size}
      caption={onBoard}
      label={!onBoard}
      live={act.cardLive(c.uid)}
      selected={act.cardSelected(c.uid)}
      onClick={() => act.onCard(c.uid)}
      drop={onBoard ? `courtier:${c.uid}` : undefined}
      dropLive={onBoard && act.dropLive(`courtier:${c.uid}`)}
      draggable={act.canDrag(c.uid)}
      onPress={(e) => act.onPress(c.uid, e)}
      popover={act.popover(c.uid)}
    />
  );
}

/** Your hand. On a phone it sits in the dock, under your thumb. */
export function Hand({ view, act, marks = NO_MARKS }: { view: View; act: Interaction; marks?: Marks }) {
  // --n: how many cards the dock's row shares its width between.
  const style = { "--n": Math.max(view.hand.length, 5) } as React.CSSProperties;
  return (
    <section className="mine" aria-label="Your hand" style={style}>
      <h2>Your hand</h2>
      <div className="row">
        {view.hand.length ? view.hand.map((c) => cardFor(act, c, "lg", false, marks)) : <p className="muted">No cards.</p>}
      </div>
    </section>
  );
}

export function Board({
  view,
  act,
  playing = null,
  won,
  hand = true,
  marks = NO_MARKS,
  suspicions,
}: {
  view: View;
  act: Interaction;
  playing?: number | null;
  won?: Map<number, string>;
  /** False when the hand is drawn elsewhere (a phone's dock). */
  hand?: boolean;
  marks?: Marks;
  suspicions?: Suspicions;
}) {
  const turn = playing ?? (view.over ? null : view.current);
  const { art } = useUi();
  const card = (c: Card, size: "sm" | "md" | "lg", onBoard = true) => cardFor(act, c, size, onBoard, marks);
  // In the order they play, starting after you.
  const n = view.players.length;
  const from = view.you >= 0 ? view.you : 0;
  const opponents = view.players
    .filter((p) => p.seat !== view.you)
    .sort((a, b) => ((a.seat - from + n) % n) - ((b.seat - from + n) % n));
  const nextSeat = turn === null ? null : (turn + 1) % n;
  const me = view.you >= 0 ? view.players[view.you] : null;

  return (
    <div className="board">
      <section className="opponents" aria-label="Opponents">
        {opponents.map((p) => (
          <Opponent
            key={p.seat}
            view={view}
            player={p}
            act={act}
            turn={turn}
            next={p.seat === nextSeat}
            suspicions={suspicions}
          />
        ))}
        <div className="status" aria-label="Table status">
          <span className="pile" title="Draw pile">
            <CardBack size="xxs" label="Deck" />
            {view.deck}
          </span>
          <span className="turn" title={`Turn ${view.turn}`}>
            Round {view.round}
            {view.max_rounds ? <small> of {view.max_rounds}</small> : null}
          </span>
          {view.removed > 0 && <span className="muted">{view.removed} out</span>}
          {view.frozen.board ? (
            <span className="seal">Siege</span>
          ) : view.frozen.inner ? (
            <span className="seal">Quarantine</span>
          ) : null}
        </div>
      </section>

      <section className="court" aria-label="Inner circle">
        <h2>The inner circle</h2>
        <CourtTally view={view} />
        <div className="seats">
          {view.seats.map((s, i) => {
            const live = act.seatLive(s.seat);
            const classes = ["seat", `estate-${s.estate.toLowerCase()}`];
            const winner = s.courtier ? won?.get(s.courtier.uid) : undefined;
            if (winner) classes.push("won-by");
            if (live) classes.push("live");
            if (act.seatSelected(s.seat)) classes.push("selected");
            if (!s.courtier) classes.push("vacant");
            if (act.dropLive(`seat:${s.seat}`)) classes.push("drop-live");
            const src = art.thumb(art.seat(s.seat));
            return (
              <div
                key={s.seat}
                className={classes.join(" ")}
                data-drop={`seat:${s.seat}`}
                style={winner ? ({ "--win": winner, "--i": i } as React.CSSProperties) : undefined}
              >
                <div className="seat-label">
                  {s.seat}
                  <small>{s.estate}</small>
                </div>
                {s.courtier ? (
                  card(s.courtier, "md")
                ) : (
                  <button
                    type="button"
                    className="card size-md chair"
                    disabled={!live}
                    onClick={() => act.onSeat(s.seat)}
                    aria-label={live ? `Choose ${s.seat}` : `${s.seat}, empty`}
                  >
                    <span className="face">{src ? <img src={src} alt="" /> : <span className="text-face">Empty</span>}</span>
                  </button>
                )}
                {s.courtier && live && (
                  <button type="button" className="seat-take" onClick={() => act.onSeat(s.seat)}>
                    Choose {s.seat}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <section
        className={`outer${act.dropLive("outer") ? " drop-live" : ""}`}
        aria-label="Outer circle"
        data-drop="outer"
      >
        <h2>
          The outer circle
          {act.dropLive("outer") && <span className="drop-hint"> · drop to play here</span>}
        </h2>
        <div className="row">
          {view.outer.length ? view.outer.map((c) => card(c, "md")) : <p className="muted">Nobody waits outside.</p>}
        </div>
      </section>

      {me && hand && <Hand view={view} act={act} marks={marks} />}
    </div>
  );
}
