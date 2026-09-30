// The table's side panels: the bot speed, your agenda and the game log.

import { useState } from "react";
import { readableLog } from "../names";
import type { View } from "../protocol";
import { SPEEDS, type LogLine, type Speed } from "../useGameFlow";
import { AgendaTracker } from "./AgendaTracker";

export function SpeedControl({ speed, onChange }: { speed: Speed; onChange(speed: Speed): void }) {
  return (
    <label>
      Bot speed{" "}
      <select aria-label="Bot speed" value={speed} onChange={(e) => onChange(e.target.value as Speed)}>
        {Object.keys(SPEEDS).map((s) => (
          <option key={s}>{s}</option>
        ))}
      </select>
    </label>
  );
}

/** Everything that has happened, newest first. */
export function GameLog({ log }: { log: LogLine[] }) {
  if (!log.length) return <p className="log-empty muted">Nothing has happened yet.</p>;
  return (
    <ol className="log" reversed aria-label="Game log">
      {log
        .slice()
        .reverse()
        .map((line, i) => (
          <li key={log.length - i}>{readableLog(line.view, line.text)}</li>
        ))}
    </ol>
  );
}

/** Your agenda and the log share one slot under the question, a tab each. */
export function AgendaAndLog({ view, log }: { view: View; log: LogLine[] }) {
  const [tab, setTab] = useState<"agenda" | "log">("agenda");
  const myAgenda = view.you >= 0 ? view.players[view.you].agenda : null;
  const showing = myAgenda ? tab : "log";
  return (
    <section className="tabbed" aria-label="Agenda and log">
      <div className="tabs" role="tablist">
        {myAgenda && (
          <button
            type="button"
            role="tab"
            id="tab-agenda"
            aria-selected={showing === "agenda"}
            aria-controls="tabpanel"
            onClick={() => setTab("agenda")}
          >
            Agenda{" "}
            <small className={myAgenda.met ? "met" : ""}>
              {myAgenda.status.filter((c) => c.met).length}/{myAgenda.status.length}
            </small>
          </button>
        )}
        <button
          type="button"
          role="tab"
          id="tab-log"
          aria-selected={showing === "log"}
          aria-controls="tabpanel"
          onClick={() => setTab("log")}
        >
          Log
        </button>
      </div>
      <div className="tabpanel" id="tabpanel" role="tabpanel" aria-labelledby={`tab-${showing}`}>
        {showing === "agenda" && myAgenda ? <AgendaTracker agenda={myAgenda} /> : <GameLog log={log} />}
      </div>
    </section>
  );
}
