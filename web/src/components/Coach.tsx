import { useEffect, useState } from "react";
import type { Coach } from "../protocol";

// The tutorial's guide, above the question: which step, and what to do next.
// The move it asks for is the only one lit on the board. On a phone it folds
// to its title with a tap, to give the board the room; each new step opens it.
export function CoachPanel({ coach, foldable = false }: { coach: Coach; foldable?: boolean }) {
  const [folded, setFolded] = useState(false);
  useEffect(() => setFolded(false), [coach.step, coach.title]);
  const kicker = `Tutorial · ${coach.step === 0 ? "the table" : `step ${coach.step} of 4`}`;

  if (foldable) {
    return (
      <section className={`coach${folded ? " folded" : ""}`} data-testid="coach" aria-live="polite">
        <button type="button" className="coach-fold" aria-expanded={!folded} onClick={() => setFolded(!folded)}>
          <span className="kicker">{kicker}</span>
          <h2>{coach.title}</h2>
          <span className="fold-mark" aria-hidden="true">
            {folded ? "▴" : "▾"}
          </span>
        </button>
        {!folded && <p>{coach.text}</p>}
      </section>
    );
  }
  return (
    <section className="coach" data-testid="coach" aria-live="polite">
      <span className="kicker">{kicker}</span>
      <h2>{coach.title}</h2>
      <p>{coach.text}</p>
    </section>
  );
}
