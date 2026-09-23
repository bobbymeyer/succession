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
  all: string[];
}

/** No pictures: every card is drawn as type. */
export const NO_ART: Art = { card: () => null, agenda: () => null, seat: () => null, back: null, all: [] };

export async function loadArt(): Promise<Art> {
  const base = new URL("cards/", new URL(import.meta.env.BASE_URL, document.baseURI));
  const response = await fetch(new URL("manifest.json", base));
  if (!response.ok) return NO_ART;
  const manifest = (await response.json()) as Manifest;
  const url = (file: string | undefined) => (file ? new URL(file, base).href : null);
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
    all: files.map((f) => url(f)!),
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
