import { useState } from "react";
import type { GameRecord, TableOptions } from "../protocol";
import { tierName } from "../names";
import { useUi } from "../art";
import { FrameControls } from "./Frame";

interface Props {
  options: TableOptions;
  saved: number | null; // finished games kept in this browser; null if storage is off
  onDeal(players: string[], seed?: number): void;
  onLoad(record: GameRecord): void;
  onExport(): void;
  onClear(): void;
  onIntro(): void;
}

const DEFAULT_BOTS = ["naive", "greedy", "strategic"];

export function Setup({ options, saved, onDeal, onLoad, onExport, onClear, onIntro }: Props) {
  const bots = options.player_types.filter((t) => t !== "human");
  const [table, setTable] = useState<string[]>(DEFAULT_BOTS);
  const [seed, setSeed] = useState("");
  const [record, setRecord] = useState("");
  const [recordError, setRecordError] = useState("");
  const size = table.length + 1;
  const { art } = useUi();

  const deal = () => {
    const n = seed.trim() === "" ? undefined : Number(seed);
    onDeal(["human", ...table], Number.isInteger(n) ? n : undefined);
  };

  const load = () => {
    try {
      onLoad(JSON.parse(record) as GameRecord);
    } catch {
      setRecordError("That isn't a game record.");
    }
  };

  return (
    <div className="setup">
      <header className="title">
        {art.back && <img src={art.back} alt="" />}
        <div>
          <h1>Court of Succession</h1>
          <p className="lede">A playtest table: you against the simulator's bots. Seats are drawn at random.</p>
          <button type="button" className="link watch-intro" data-testid="watch-intro" onClick={onIntro}>
            Watch introduction
          </button>
        </div>
      </header>

      <h2>The table</h2>
      <ol className="seats-list">
        <li>
          <span>You</span>
        </li>
        {table.map((tier, i) => (
          <li key={i}>
            <select
              aria-label={`Bot ${i + 1}`}
              value={tier}
              onChange={(e) => setTable(table.map((t, j) => (j === i ? e.target.value : t)))}
            >
              {bots.map((b) => (
                <option key={b} value={b}>
                  {tierName(b)}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={size <= options.min_players}
              onClick={() => setTable(table.filter((_, j) => j !== i))}
              aria-label={`Remove bot ${i + 1}`}
            >
              Remove
            </button>
          </li>
        ))}
      </ol>
      <button type="button" disabled={size >= options.max_players} onClick={() => setTable([...table, "greedy"])}>
        Add a bot
      </button>
      <p className="hint">
        {size} players ({options.min_players}–{options.max_players}). Naive plays at random, greedy chases its own
        agenda, strategic also blocks everyone else's.
      </p>

      <label className="seed">
        Seed <input inputMode="numeric" placeholder="random" value={seed} onChange={(e) => setSeed(e.target.value)} />
      </label>
      <div className="buttons">
        <button type="button" className="primary" data-testid="deal" onClick={deal}>
          Deal
        </button>
        <FrameControls />
      </div>

      <details className="load">
        <summary>Load a saved game</summary>
        <textarea
          aria-label="Game record"
          rows={4}
          value={record}
          onChange={(e) => {
            setRecord(e.target.value);
            setRecordError("");
          }}
        />
        {recordError && <p className="error">{recordError}</p>}
        <button type="button" disabled={!record.trim()} onClick={load}>
          Load
        </button>
      </details>

      {saved ? (
        <details className="load">
          <summary>
            Your games ({saved} finished in this browser)
          </summary>
          <p className="hint">
            Download them as the simulator's own log -- <code>python -m succession analyze games.csv</code> -- to set
            human results beside the bots'.
          </p>
          <div className="buttons">
            <button type="button" onClick={onExport}>
              Download games as CSV
            </button>
            <button type="button" onClick={() => window.confirm(`Forget all ${saved} games?`) && onClear()}>
              Forget them
            </button>
          </div>
        </details>
      ) : null}
    </div>
  );
}
