// Card pictures: the composed cards `tools/mpcfill.py --profile game` writes
// into public/cards, looked up by the name the engine reports.

import { createContext, useContext } from "react";
import type { Card } from "./protocol";

interface Manifest {
  cards: Record<string, string>;
  agendas: Record<string, string>;
  seats: Record<string, string>;
  back: string;
}

export interface Art {
  card(name: string): string | null;
  agenda(name: string): string | null;
  seat(name: string): string | null;
  back: string | null;
  /**
   * The copy of a picture to draw it small: on a phone, the 320px one in
   * cards/sm/; elsewhere the picture itself. Large views (the inspector, an
   * event, the briefing) take the full card.
   */
  thumb(src: string | null): string | null;
  all: string[];
  /** Every picture at every size this screen may draw, for the offline cache. */
  offline: string[];
}

/** No pictures: every card is drawn as type. */
export const NO_ART: Art = {
  card: () => null,
  agenda: () => null,
  seat: () => null,
  back: null,
  thumb: (src) => src,
  all: [],
  offline: [],
};

/** A phone, either way up: its cards are drawn small. */
export const SMALL_SCREEN = "(max-width: 600px), (max-height: 500px)";

export async function loadArt(): Promise<Art> {
  const base = new URL("cards/", new URL(import.meta.env.BASE_URL, document.baseURI));
  const response = await fetch(new URL("manifest.json", base));
  if (!response.ok) return NO_ART;
  const manifest = (await response.json()) as Manifest;
  const url = (file: string | undefined) => (file ? new URL(file, base).href : null);
  const small = window.matchMedia?.(SMALL_SCREEN).matches ?? false;
  const smallBase = new URL("sm/", base).href;
  const thumb = (src: string | null) => (small && src?.startsWith(base.href) ? smallBase + src.slice(base.href.length) : src);
  const files = [
    ...Object.values(manifest.cards),
    ...Object.values(manifest.agendas),
    ...Object.values(manifest.seats),
    manifest.back,
  ];
  return {
    card: (name) => url(manifest.cards[name]),
    agenda: (name) => url(manifest.agendas[name]),
    seat: (name) => url(manifest.seats[name]),
    back: url(manifest.back),
    thumb,
    // What a game draws at once: the small copies, on a phone.
    all: files.map((f) => thumb(url(f))!),
    offline: [...new Set(files.flatMap((f) => [url(f)!, thumb(url(f))!]))],
  };
}

/** Warm the cache so a bot's card appears the moment it is played. */
export function preload(art: Art) {
  for (const src of art.all) {
    const image = new Image();
    image.decoding = "async";
    image.src = src;
  }
}

// -- what every card on the page can reach -----------------------------------
export interface Ui {
  art: Art;
  /** Open a card large, with its live attributes. */
  inspect(card: Card): void;
  /** The card under the pointer, for the side preview. */
  hover(card: Card | null): void;
}

export const UiContext = createContext<Ui>({ art: NO_ART, inspect: () => {}, hover: () => {} });
export const useUi = () => useContext(UiContext);
