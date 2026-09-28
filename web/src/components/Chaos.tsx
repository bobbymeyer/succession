import { Story, storyImage, type Beat } from "./Story";

// When the round limit runs out with no agenda met: the young king, left
// without counsel, and the kingdom with him. Everyone loses.

const BEATS: Beat[] = [
  {
    image: "tyrant",
    focus: "center 22%",
    lines: ["Without effective council,", "the young king grows indulgent and tyrannical,"],
    at: [500, 2200],
    hold: 6200,
  },
  {
    image: "mob",
    focus: "center 55%",
    lines: ["and the kingdom slips into chaos."],
    at: [600],
    hold: 4600,
  },
];

export function Chaos({ rounds, onDone }: { rounds: number; onDone(): void }) {
  return (
    <Story
      beats={BEATS}
      endImages={["ruin"]}
      label="Chaos"
      testId="chaos"
      className="chaos"
      onDone={onDone}
      end={
        <>
          <div
            className="intro-art on"
            style={{ backgroundImage: `url(${storyImage("ruin")})`, backgroundPosition: "center 30%" }}
            aria-hidden="true"
          />
          <div className="intro-shade" aria-hidden="true" />
          <div className="intro-title chaos-title">
            <h1>Everyone loses</h1>
            <p>
              {rounds} {rounds === 1 ? "round" : "rounds"}, and no faction secured the throne.
            </p>
            <button
              type="button"
              className="primary"
              data-testid="chaos-done"
              autoFocus
              onClick={(e) => {
                e.stopPropagation();
                onDone();
              }}
            >
              Look upon the court
            </button>
          </div>
        </>
      }
    />
  );
}
