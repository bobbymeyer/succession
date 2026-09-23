import { useEffect, useState } from "react";

/** True when the game runs inside another page's iframe. */
function framed(): boolean {
  try {
    return window.self !== window.top;
  } catch {
    return true; // a cross-origin parent will not even say
  }
}

// Room to play. Full screen works in a tab, and in an iframe that grants it
// (allow="fullscreen"); inside a small frame, a new tab is the other way out.
export function FrameControls() {
  const [full, setFull] = useState(() => Boolean(document.fullscreenElement));
  useEffect(() => {
    const change = () => setFull(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", change);
    return () => document.removeEventListener("fullscreenchange", change);
  }, []);

  const toggle = () => {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    else document.documentElement.requestFullscreen().catch(() => {});
  };

  return (
    <>
      {document.fullscreenEnabled && (
        <button type="button" onClick={toggle} aria-pressed={full}>
          {full ? "Exit full screen" : "Full screen"}
        </button>
      )}
      {framed() && (
        <a className="button" href={window.location.href} target="_blank" rel="noopener">
          Open in a new tab
        </a>
      )}
    </>
  );
}
