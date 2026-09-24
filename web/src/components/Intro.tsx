import { useCallback, useEffect, useRef, useState } from "react";

// The story before the first game: a few beats over the card paintings,
// ending on the title. It plays by itself; a click, Space or the arrow keys
// hurry it along, and Skip leaves at once. It shows on a first visit only,
// or when asked for from the setup screen.

const SEEN = "succession.introSeen";

export function introSeen(): boolean {
  try {
    return localStorage.getItem(SEEN) === "1";
  } catch {
    return false; // no storage: show it, it can always be skipped
  }
}

function markSeen() {
  try {
    localStorage.setItem(SEEN, "1");
  } catch {
    // not remembered; it shows again next time
  }
}

interface Beat {
  image: string;
  /** What to keep in view when a wide screen crops the portrait painting. */
  focus: string;
  lines: string[];
  /** When each line fades in, in ms from the start of the beat. */
  at: number[];
  /** How long the beat holds before the next one, in ms. */
  hold: number;
}

const BEATS: Beat[] = [
  {
    image: "eclipse",
    focus: "center 18%",
    lines: ["The King has died, leaving his infant son to inherit the throne."],
    at: [700],
    hold: 6000,
  },
  {
    image: "outmaneuver",
    focus: "center 68%",
    lines: ["The powerful men of the empire…", "like you…", "are scheming for the ear of the young monarch."],
    at: [500, 2300, 3700],
    hold: 8000,
  },
  {
    image: "promotion",
    focus: "center 38%",
    lines: ["You must place your agents in offices close to the king", "to secure your interests"],
    at: [500, 3200],
    hold: 7000,
  },
  {
    image: "assassination",
    focus: "center 45%",
    lines: ["and ensure your faction's survival in the…"],
    at: [500],
    hold: 4200,
  },
];

const url = (name: string) => `./intro/${name}.webp`;

export function Intro({ onDone }: { onDone(): void }) {
  // BEATS.length is the title.
  const [beat, setBeat] = useState(0);
  const [shown, setShown] = useState(0); // lines of this beat on screen
  const title = beat >= BEATS.length;

  const finish = useCallback(() => {
    markSeen();
    onDone();
  }, [onDone]);

  // Lines come in on their own time, then the next beat.
  useEffect(() => {
    if (title) return;
    const b = BEATS[beat];
    const timers = b.at.map((t, i) => window.setTimeout(() => setShown((n) => Math.max(n, i + 1)), t));
    timers.push(window.setTimeout(() => next(), b.hold));
    return () => timers.forEach(window.clearTimeout);
  }, [beat]);

  // A click shows the rest of this beat, or moves on if it is all there.
  const next = () => {
    setBeat((b) => Math.min(b + 1, BEATS.length));
    setShown(0);
  };
  const hurry = () => {
    if (title) return;
    if (shown < BEATS[beat].lines.length) setShown(BEATS[beat].lines.length);
    else next();
  };

  // One listener for the life of the intro, reading the latest state
  // through a ref. Re-adding it on every render would drop a key press that
  // arrives while another listener's update re-renders the page.
  const onKey = useRef<(e: KeyboardEvent) => void>(() => {});
  onKey.current = (e) => {
    if (e.key === "Escape") finish();
    else if (e.key === " " || e.key === "ArrowRight" || e.key === "Enter") {
      if (title && e.key !== "ArrowRight") finish();
      else hurry();
      e.preventDefault();
    }
  };
  useEffect(() => {
    const key = (e: KeyboardEvent) => onKey.current(e);
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);

  // Every picture starts loading at once, so no beat waits on its own.
  useEffect(() => {
    for (const b of [...BEATS.map((b) => b.image), "emblem"]) new Image().src = url(b);
  }, []);

  return (
    <div className="intro" data-testid="intro" onClick={hurry} role="dialog" aria-label="Introduction">
      {BEATS.map((b, i) => (
        <div
          key={b.image}
          className={`intro-art${i === beat ? " on" : ""}`}
          style={{ backgroundImage: `url(${url(b.image)})`, backgroundPosition: b.focus }}
          aria-hidden="true"
        />
      ))}
      <div className="intro-shade" aria-hidden="true" />

      {!title && (
        <div className="intro-lines" key={beat} aria-live="polite">
          {BEATS[beat].lines.map((line, i) => (
            <p key={line} className={i < shown ? "on" : ""}>
              {line}
            </p>
          ))}
        </div>
      )}

      {title && (
        <div className="intro-title">
          <img src={url("emblem")} alt="" />
          <h1>Succession</h1>
          <button
            type="button"
            className="primary"
            data-testid="enter"
            autoFocus
            onClick={(e) => {
              e.stopPropagation();
              finish();
            }}
          >
            Enter the court
          </button>
        </div>
      )}

      {!title && (
        <button
          type="button"
          className="intro-skip"
          data-testid="skip-intro"
          onClick={(e) => {
            e.stopPropagation();
            finish();
          }}
        >
          Skip
        </button>
      )}
      <div className="intro-dots" aria-hidden="true">
        {[...BEATS, null].map((_, i) => (
          <span key={i} className={i === beat ? "on" : ""} />
        ))}
      </div>
    </div>
  );
}
