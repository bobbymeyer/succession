import type { View } from "../protocol";
import { playerName } from "../names";
import { CardView } from "./CardView";

export interface Interaction {
  cardLive(uid: number): boolean;
  cardSelected(uid: number): boolean;
  onCard(uid: number): void;
  seatLive(seat: string): boolean;
  seatSelected(seat: string): boolean;
  onSeat(seat: string): void;
}

export const NO_INTERACTION: Interaction = {
  cardLive: () => false,
  cardSelected: () => false,
  onCard: () => {},
  seatLive: () => false,
  seatSelected: () => false,
  onSeat: () => {},
};

export function Board({ view, act }: { view: View; act: Interaction }) {
  const card = (c: Parameters<typeof CardView>[0]["card"]) => (
    <CardView
      key={c.uid}
      card={c}
      live={act.cardLive(c.uid)}
      selected={act.cardSelected(c.uid)}
      onClick={() => act.onCard(c.uid)}
    />
  );

  return (
    <div className="board">
      <section className="players" aria-label="Players">
        {view.players.map((p) => {
          const classes = ["player"];
          if (p.seat === view.current && !view.over) classes.push("current");
          if (p.seat === view.you) classes.push("you");
          if (view.winners.includes(p.seat)) classes.push("winner");
          return (
            <div key={p.seat} className={classes.join(" ")}>
              <strong>{playerName(view, p.seat)}</strong>
              <span>{p.hand} in hand</span>
              <span className="agenda">{p.agenda ? p.agenda.name : "Agenda hidden"}</span>
              {p.skips_next_turn && <span className="flag">Skips next turn</span>}
            </div>
          );
        })}
      </section>

      <section className="status" aria-label="Table status">
        <span>Turn {view.turn}</span>
        <span>Deck {view.deck}</span>
        <span>
          Discard {view.discard}
          {view.discard_top ? ` (top: ${view.discard_top.name})` : ""}
        </span>
        {view.removed > 0 && <span>Out of the game {view.removed}</span>}
        {view.frozen.board ? (
          <span className="flag">Siege: the whole board is sealed</span>
        ) : view.frozen.inner ? (
          <span className="flag">Quarantine: the inner circle is sealed</span>
        ) : null}
      </section>

      <section className="inner" aria-label="Inner circle">
        <h2>Inner circle</h2>
        <div className="seats">
          {view.seats.map((s) => {
            const live = act.seatLive(s.seat);
            const classes = ["seat", `estate-${s.estate.toLowerCase()}`];
            if (live) classes.push("live");
            if (act.seatSelected(s.seat)) classes.push("selected");
            const label = (
              <span className="seat-name">
                {s.seat} <small>{s.estate}</small>
              </span>
            );
            return (
              <div key={s.seat} className={classes.join(" ")}>
                {live ? (
                  <button type="button" className="seat-button" onClick={() => act.onSeat(s.seat)}>
                    {label}
                  </button>
                ) : (
                  label
                )}
                {s.courtier ? card(s.courtier) : <div className="empty">Empty</div>}
              </div>
            );
          })}
        </div>
      </section>

      <section className="outer" aria-label="Outer circle">
        <h2>Outer circle</h2>
        <div className="row">{view.outer.length ? view.outer.map(card) : <div className="empty">Nobody</div>}</div>
      </section>

      {view.you >= 0 && (
        <section className="mine" aria-label="Your hand">
          <h2>
            Your hand <span className="agenda">Agenda: {view.players[view.you].agenda?.name}</span>
          </h2>
          <div className="row">{view.hand.length ? view.hand.map(card) : <div className="empty">No cards</div>}</div>
        </section>
      )}
    </div>
  );
}
