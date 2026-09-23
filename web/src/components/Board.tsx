import type { Card, Player, View } from "../protocol";
import { useUi } from "../art";
import { playerName, tierName } from "../names";
import { CardBack, CardView } from "./CardView";

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
function Opponent({ view, player }: { view: View; player: Player }) {
  const classes = ["opponent"];
  if (player.seat === view.current && !view.over) classes.push("current");
  if (view.winners.includes(player.seat)) classes.push("winner");
  return (
    <div className={classes.join(" ")} data-player={player.seat} aria-label={playerName(view, player.seat)}>
      <span className="who">
        <strong>P{player.seat}</strong> {tierName(player.tier).replace(" bot", "")}
      </span>
      <span className="hand-count" title={`${player.hand} cards in hand`}>
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

export function Board({ view, act }: { view: View; act: Interaction }) {
  const { art } = useUi();
  const card = (c: Card, size: "sm" | "md" | "lg", caption = true) => (
    <CardView
      key={c.uid}
      card={c}
      size={size}
      caption={caption}
      live={act.cardLive(c.uid)}
      selected={act.cardSelected(c.uid)}
      onClick={() => act.onCard(c.uid)}
    />
  );
  const opponents = view.players.filter((p) => p.seat !== view.you);
  const me = view.you >= 0 ? view.players[view.you] : null;

  return (
    <div className="board">
      <section className="opponents" aria-label="Opponents">
        {opponents.map((p) => (
          <Opponent key={p.seat} view={view} player={p} />
        ))}
        <div className="status" aria-label="Table status">
          <span className="pile" title="Draw pile">
            <CardBack size="xxs" label="Deck" />
            {view.deck}
          </span>
          <span className="pile" title={view.discard_top ? `Discard pile, top: ${view.discard_top.name}` : "Discard pile"}>
            {view.discard_top ? <CardView card={view.discard_top} size="xxs" /> : <span className="card size-xxs empty-slot" />}
            {view.discard}
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
          {view.seats.map((s) => {
            const live = act.seatLive(s.seat);
            const classes = ["seat", `estate-${s.estate.toLowerCase()}`];
            if (live) classes.push("live");
            if (act.seatSelected(s.seat)) classes.push("selected");
            if (!s.courtier) classes.push("vacant");
            const src = art.seat(s.seat);
            return (
              <div key={s.seat} className={classes.join(" ")}>
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

      <section className="outer" aria-label="Outer circle">
        <h2>The outer circle</h2>
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
