import { useEffect, useState } from "react";

/** A phone held upright: the table is laid out to fit one screen. */
export const PHONE = "(max-width: 600px)";
/** A phone on its side: too short for the dock under the board. */
export const PHONE_LANDSCAPE = "(max-height: 500px) and (orientation: landscape) and (max-width: 1000px)";

export type PhoneLayout = "portrait" | "landscape" | null;

function current(): PhoneLayout {
  if (!window.matchMedia) return null;
  if (window.matchMedia(PHONE).matches) return "portrait";
  if (window.matchMedia(PHONE_LANDSCAPE).matches) return "landscape";
  return null;
}

/** Which phone layout the screen wants, if any; it follows a turn of the phone. */
export function usePhone(): PhoneLayout {
  const [layout, setLayout] = useState(current);
  useEffect(() => {
    if (!window.matchMedia) return;
    const queries = [window.matchMedia(PHONE), window.matchMedia(PHONE_LANDSCAPE)];
    const change = () => setLayout(current());
    queries.forEach((q) => q.addEventListener("change", change));
    return () => queries.forEach((q) => q.removeEventListener("change", change));
  }, []);
  return layout;
}
