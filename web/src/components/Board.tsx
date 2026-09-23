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
function Agenda({ player, size }: { player: Player; size: "xs" | "sm" | "md" }) {
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

function Opponent({ view, player }: { view: View; player: Player }) {
  const classes = ["opponent"];
  if (player.seat === view.current && !view.over) classes.push("current");
  if (view.winners.includes(player.seat)) classes.push("winner");
  const shown = Math.min(player.hand, 7);
  return (
    <div className={classes.join(" ")} data-player={player.seat} aria-label={playerName(view, player.seat)}>
      <div className="who">
        <strong>P{player.seat}</strong> {tierName(player.tier)}
        {player.skips_next_turn && <span className="flag">Skips next turn</span>}
      </div>
      <div className="holding">
        <div className="fan" aria-label={`${player.hand} cards in hand`}>
          {Array.from({ length: shown }, (_, i) => (
            <CardBack key={i} />
          ))}
          <span className="count">{player.hand}</span>
        </div>
        <Agenda player={player} size="xs" />
      </div>
      <div className="agenda-name">{player.agenda ? player.agenda.name : "Agenda hidden"}</div>
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
          <div className="piles">
            <div className="pile">
              <CardBack size="xs" label="Deck" />
              <span>
                Deck <strong>{view.deck}</strong>
              </span>
            </div>
            <div className="pile">
              {view.discard_top ? (
                <CardView card={view.discard_top} size="xs" />
              ) : (
                <div className="card size-xs empty-slot" />
              )}
              <span>
                Discard <strong>{view.discard}</strong>
              </span>
            </div>
          </div>
          <div className="turn">
            Turn <strong>{view.turn}</strong>
            {view.removed > 0 && <span className="muted"> · {view.removed} out of the game</span>}
          </div>
          {view.frozen.board ? (
            <div className="seal">Siege: nothing on the board can change</div>
          ) : view.frozen.inner ? (
            <div className="seal">Quarantine: the inner circle is sealed</div>
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
          {view.outer.length ? view.outer.map((c) => card(c, "sm")) : <p className="muted">Nobody waits outside.</p>}
        </div>
      </section>

      {me && (
        <section className="mine" aria-label="Your hand">
          <div className="my-agenda">
            <h2>Agenda</h2>
            <Agenda player={me} size="md" />
            <div className="agenda-name">{me.agenda?.name}</div>
          </div>
          <div className="my-hand">
            <h2>Your hand</h2>
            <div className="row">{view.hand.length ? view.hand.map((c) => card(c, "lg", false)) : <p className="muted">No cards.</p>}</div>
          </div>
        </section>
      )}
    </div>
  );
}
