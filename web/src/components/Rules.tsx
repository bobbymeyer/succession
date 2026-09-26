import { useEffect, useRef } from "react";
import type { TableOptions } from "../protocol";

// How to play, in a modal. The agendas and the events come from the engine
// (webapi `options`), so their numbers are the ones the game actually plays
// by; the rest is the turn as docs/RULES.md has it, said for a player.

const SEATS: [string, string][] = [
  ["Archpriest", "Church"],
  ["Oracle", "Church"],
  ["Lord General", "Military"],
  ["Captain of the Guard", "Military"],
  ["Keeper of the Treasury", "Merchant"],
  ["Master of the Market", "Merchant"],
  ["Voice of the People", "Commons"],
];

const CARDS: [string, string][] = [
  ["Courtier", "Enters the outer circle, where anyone may seat them."],
  ["Promotion", "Moves an outer courtier into an occupied seat of their estate; the sitter is bumped to the outer circle."],
  ["Demotion", "Sends a seated courtier back to the outer circle, leaving the seat empty."],
  ["Removal", "A courtier leaves play. Targeted Poisoning allows a saving roll."],
  ["Defense", "Paid for with a courtier of the same estate from your hand, it shields a seated courtier from the next removal, demotion, strip or mutation. It does not stop events."],
  ["Strip", "Takes away a courtier's house (Castration) or faith (Excommunication)."],
  ["Mutation", "Changes one of a courtier's attributes. Each attribute can be changed only once."],
  ["Outmaneuver", "The player you name skips their next turn."],
  ["Schismatic Event", "Swap your agenda for a new secret one."],
];

export function Rules({ options, onClose }: { options: TableOptions; onClose(): void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = dialog.current;
    if (d && !d.open) d.showModal();
  }, []);
  const { rules } = options;

  return (
    <dialog ref={dialog} className="rules" data-testid="rules" onClose={onClose} aria-labelledby="rules-title">
      <header>
        <h2 id="rules-title">How to play</h2>
        <form method="dialog">
          <button type="submit" className="close" aria-label="Close the rules">
            ×
          </button>
        </form>
      </header>

      <div className="rules-body">
        <section>
          <h3>The aim</h3>
          <p>
            Every player holds a secret <strong>agenda</strong>: a shape the court could take. The moment the inner circle
            shows yours, you reveal it and win. If one board meets two agendas at once, both players win. If nobody has won
            after {rules.max_turns} turns, chaos grips the empire and nobody does.
          </p>
        </section>

        <section>
          <h3>The court</h3>
          <p>
            The <strong>inner circle</strong> is seven seats, each tied to an estate. A courtier can only sit in a seat of
            their own estate.
          </p>
          <ul className="rules-seats">
            {SEATS.map(([seat, estate]) => (
              <li key={seat}>
                <span>{seat}</span>
                <small>{estate}</small>
              </li>
            ))}
          </ul>
          <p>
            The <strong>outer circle</strong> is everyone else in play, waiting for a seat. Nobody owns a courtier: agendas
            read the board, and anyone may move any outer courtier. Every courtier has an <strong>estate</strong>, a{" "}
            <strong>faith</strong>, a <strong>house</strong> and an <strong>origin</strong>.
          </p>
        </section>

        <section>
          <h3>Your turn</h3>
          <ol>
            <li>
              <strong>Draw a card.</strong> Everyone starts with {rules.starting_hand}.
            </li>
            <li>
              <strong>Do one thing:</strong>
              <ul>
                <li>
                  <em>Play a card</em> from your hand. A courtier goes to the outer circle; nothing goes straight into a
                  seat from your hand.
                </li>
                <li>
                  <em>Move</em> an outer courtier into an empty seat of their estate. It costs no card.
                </li>
                <li>
                  <em>Discard &amp; Draw</em>: throw a card away and draw another.
                </li>
              </ul>
            </li>
            <li>
              <strong>Mind the hand limit.</strong> Nothing stops you drawing, but if you hold more than {rules.hand_limit}{" "}
              as your turn ends, you discard down to {rules.hand_limit}.
            </li>
          </ol>
          <p>An occupied seat can only be taken with a promotion.</p>
        </section>

        <section>
          <h3>Cards</h3>
          <dl className="rules-cards">
            {CARDS.map(([name, text]) => (
              <div key={name}>
                <dt>{name}</dt>
                <dd>{text}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section>
          <h3>Events</h3>
          <p>
            Nobody holds an event. <strong>It plays the moment it is drawn</strong>, for whoever drew it, and hits the
            whole table; no defense stops one. Then that player draws again and carries on. When an event asks everyone
            to choose, everyone chooses at once.
          </p>
          <dl className="rules-cards">
            {rules.events.map((e) => (
              <div key={e.name}>
                <dt>{e.name}</dt>
                <dd>{e.summary}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section>
          <h3>Agendas</h3>
          <p>Each player is dealt one of these eight. Everything an agenda asks for must hold at once, in the inner circle unless it says otherwise.</p>
          <dl className="rules-agendas">
            {rules.agendas.map((a) => (
              <div key={a.name}>
                <dt>{a.name}</dt>
                <dd>
                  <ul>
                    {a.clauses.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                </dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </dialog>
  );
}
