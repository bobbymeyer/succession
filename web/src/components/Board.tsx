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
  const src = art.agenda(player.agenda.name);
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
function Opponent({ view, player, act, turn }: { view: View; player: Player; act: Interaction; turn: number | null }) {
  const classes = ["opponent"];
  if (player.seat === turn) classes.push("current");
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
        <strong>P{player.seat}</strong> {tierName(player.tier).replace(" bot", "")}
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
        ) : (
          <span className="hidden-agenda" aria-label="Agenda hidden">
            ?
          </span>
        )}
      </span>
      {player.skips_next_turn && <span className="flag">Skips</span>}
    </div>
  );
}

// `playing` is a bot whose card is still on its way to the table: until it
// lands, it is still that bot's turn as far as anyone watching can tell.
// `won` is the court that won the game, each courtier with its winner's
// colour; they light up and bounce once the game is over.
export function Board({
  view,
  act,
  playing = null,
  won,
}: {
  view: View;
  act: Interaction;
  playing?: number | null;
  won?: Map<number, string>;
}) {
  const turn = playing ?? (view.over ? null : view.current);
  const { art } = useUi();
  // Board courtiers are places to drop an action on; hand cards are not.
  const card = (c: Card, size: "sm" | "md" | "lg", onBoard = true) => (
    <CardView
      key={c.uid}
      card={c}
      size={size}
      caption={onBoard}
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
  const opponents = view.players.filter((p) => p.seat !== view.you);
  const me = view.you >= 0 ? view.players[view.you] : null;

  return (
    <div className="board">
      <section className="opponents" aria-label="Opponents">
        {opponents.map((p) => (
          <Opponent key={p.seat} view={view} player={p} act={act} turn={turn} />
        ))}
        <div className="status" aria-label="Table status">
          <span className="pile" title="Draw pile">
            <CardBack size="xxs" label="Deck" />
            {view.deck}
          </span>
          <span className="turn">Turn {view.turn}</span>
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
            const src = art.seat(s.seat);
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

      {me && (
        <section className="mine" aria-label="Your hand">
          <h2>Your hand</h2>
          <div className="row">{view.hand.length ? view.hand.map((c) => card(c, "lg", false)) : <p className="muted">No cards.</p>}</div>
        </section>
      )}
    </div>
  );
}
