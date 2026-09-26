import type { Coach } from "../protocol";

// The tutorial's guide, above the question: which step, and what to do next.
// The move it asks for is the only one lit on the board.
export function CoachPanel({ coach }: { coach: Coach }) {
  return (
    <section className="coach" data-testid="coach" aria-live="polite">
      <span className="kicker">
        Tutorial · {coach.step === 0 ? "the table" : `step ${coach.step} of 4`}
      </span>
      <h2>{coach.title}</h2>
      <p>{coach.text}</p>
    </section>
  );
}
