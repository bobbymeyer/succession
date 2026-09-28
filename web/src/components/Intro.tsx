import { Story, storyImage, type Beat } from "./Story";

// The story before the first game, ending on the title. It shows on a first
// visit only, or when asked for from the setup screen.

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
    lines: ["The powerful men of the empire…", "like you…", "are intriguing for the ear of the young monarch."],
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

export function Intro({ onDone }: { onDone(): void }) {
  const finish = () => {
    markSeen();
    onDone();
  };
  return (
    <Story
      beats={BEATS}
      endImages={["emblem"]}
      label="Introduction"
      testId="intro"
      onDone={finish}
      end={
        <div className="intro-title">
          <img src={storyImage("emblem")} alt="" />
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
      }
    />
  );
}
