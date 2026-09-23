import type { Agenda } from "../protocol";
import { useUi } from "../art";

// Your agenda, clause by clause against the board as it stands: what is met,
// what is not, and who is waiting in the outer circle to help. The engine
// works the clauses out (succession/agendas.py `conditions`); all of them met
// is exactly the win.
export function AgendaTracker({ agenda }: { agenda: Agenda }) {
  const { art, inspect } = useUi();
  const src = art.agenda(agenda.name);
  const met = agenda.status.filter((c) => c.met).length;
  return (
    <div className={`tracker${agenda.met ? " done" : ""}`} data-testid="agenda-tracker">
      <div className="tracker-head">
        {src && (
          <button
            type="button"
            className="tracker-card"
            onClick={() => inspect({ uid: -1, name: agenda.name, kind: "Agenda", estate: null })}
            aria-label={`Look at ${agenda.name}`}
          >
            <img src={src} alt="" />
          </button>
        )}
        <div>
          <strong>{agenda.name}</strong>
          <div className="tracker-score">
            {agenda.met ? "All met" : `${met} of ${agenda.status.length} met`}
          </div>
        </div>
      </div>
      <ul className="clauses">
        {agenda.status.map((c) => (
          <li key={c.label} className={c.met ? "met" : ""}>
            <span className="mark" aria-hidden="true">
              {c.met ? "✓" : "○"}
            </span>
            <span className="clause">
              {c.label}
              {!c.met && c.waiting ? <small> · {c.waiting} waiting outside</small> : null}
            </span>
            <span className="count" aria-label={`${c.have} of ${c.need}`}>
              {Math.min(c.have, 99)}/{c.need}
            </span>
            <span className="bar" aria-hidden="true">
              <span style={{ width: `${Math.min(1, c.have / c.need) * 100}%` }} />
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
