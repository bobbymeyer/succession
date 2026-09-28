import { useEffect, useRef, useState, type ReactNode } from "react";

// A short told sequence over the card paintings: a few beats, each line
// fading in on its own time, ending on a card of its own (`end`). It plays by
// itself; a click, Space or the arrow keys hurry it along, and Skip or Escape
// leaves at once. The introduction and the fall into chaos are both one.

export interface Beat {
  image: string;
  /** What to keep in view when a wide screen crops the portrait painting. */
  focus: string;
  lines: string[];
  /** When each line fades in, in ms from the start of the beat. */
  at: number[];
  /** How long the beat holds before the next one, in ms. */
  hold: number;
}

export const storyImage = (name: string) => `./intro/${name}.webp`;

interface Props {
  beats: Beat[];
  /** The last card, once the beats are told. */
  end: ReactNode;
  /** Pictures the end shows, loaded up front with the beats'. */
  endImages?: string[];
  label: string;
  testId: string;
  className?: string;
  onDone(): void;
}

export function Story({ beats, end, endImages = [], label, testId, className, onDone }: Props) {
  // beats.length is the end.
  const [beat, setBeat] = useState(0);
  const [shown, setShown] = useState(0); // lines of this beat on screen
  const atEnd = beat >= beats.length;

  // Lines come in on their own time, then the next beat.
  useEffect(() => {
    if (atEnd) return;
    const b = beats[beat];
    const timers = b.at.map((t, i) => window.setTimeout(() => setShown((n) => Math.max(n, i + 1)), t));
    timers.push(window.setTimeout(() => next(), b.hold));
    return () => timers.forEach(window.clearTimeout);
  }, [beat]);

  // A click shows the rest of this beat, or moves on if it is all there.
  const next = () => {
    setBeat((b) => Math.min(b + 1, beats.length));
    setShown(0);
  };
  const hurry = () => {
    if (atEnd) return;
    if (shown < beats[beat].lines.length) setShown(beats[beat].lines.length);
    else next();
  };

  // One listener for the life of the story, reading the latest state
  // through a ref. Re-adding it on every render would drop a key press that
  // arrives while another listener's update re-renders the page.
  const onKey = useRef<(e: KeyboardEvent) => void>(() => {});
  onKey.current = (e) => {
    if (e.key === "Escape") onDone();
    else if (e.key === " " || e.key === "ArrowRight" || e.key === "Enter") {
      if (atEnd && e.key !== "ArrowRight") onDone();
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
    for (const b of [...beats.map((b) => b.image), ...endImages]) new Image().src = storyImage(b);
  }, []);

  return (
    <div className={`intro${className ? ` ${className}` : ""}`} data-testid={testId} onClick={hurry} role="dialog" aria-label={label}>
      {beats.map((b, i) => (
        <div
          key={b.image}
          className={`intro-art${i === beat ? " on" : ""}`}
          style={{ backgroundImage: `url(${storyImage(b.image)})`, backgroundPosition: b.focus }}
          aria-hidden="true"
        />
      ))}
      <div className="intro-shade" aria-hidden="true" />

      {!atEnd && (
        <div className="intro-lines" key={beat} aria-live="polite">
          {beats[beat].lines.map((line, i) => (
            <p key={line} className={i < shown ? "on" : ""}>
              {line}
            </p>
          ))}
        </div>
      )}

      {atEnd && end}

      {!atEnd && (
        <button
          type="button"
          className="intro-skip"
          data-testid={`skip-${testId}`}
          onClick={(e) => {
            e.stopPropagation();
            onDone();
          }}
        >
          Skip
        </button>
      )}
      <div className="intro-dots" aria-hidden="true">
        {[...beats, null].map((_, i) => (
          <span key={i} className={i === beat ? "on" : ""} />
        ))}
      </div>
    </div>
  );
}
