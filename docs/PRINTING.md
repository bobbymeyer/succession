# Printing a playtest deck

`tools/mpcfill.py` turns the art in `assets/` into a deck you can order from
[MakePlayingCards](https://www.makeplayingcards.com) with
[MPC Autofill](https://github.com/chilli-axe/mpc-autofill). It composes each
card front -- name, type line, and either the courtier's attributes or the
card's rules text -- over the illustration, then writes the XML order file that
MPC Autofill's desktop tool feeds to the MPC site.

The art alone is not a deck. None of it carries a name, an estate or a line of
rules, and a courtier's four printed attributes are the whole of what an agenda
reads off the board, so they have to be on the card.

## 1. Build the images and the order file

```bash
pip install pillow          # the only dependency, and only for this script
python tools/mpcfill.py
```

That writes, by default:

```
build/mpc/
    cards/00 Cardback.png              the shared back
    cards/01 Beloved of the Gods.png   one front per deck slot, 84 of them
    ...
    cards/85 House Rising -- Amonides.png   the 8 agenda cards
    ...
    succession.xml                     the order file
```

92 cards: the 84-card play deck plus the eight agendas. `--no-agendas` drops
them back to 84.

`build/` is gitignored -- the fronts are large and entirely derived from
`assets/` plus the deck, so there is no reason to commit them.

The script reads the deck from `succession/cards.py`, so what it prints is what
the simulator plays. Art file `NN_...` goes to deck slot `NN - 1`, and the
script checks each file's kind and slug against the card before using it: if
the numbering ever slips, it stops and names the slots rather than printing
forty portraits one seat to the left. `tests/test_card_text.py` pins the same
check.

## 2. Run MPC Autofill

Download the `autofill` executable for your platform from
[the releases page](https://github.com/chilli-axe/mpc-autofill/releases), put it
in `build/mpc/` next to `succession.xml`, and run it.

* On Linux you have to launch it from a terminal: `./autofill-linux.bin`.
* On macOS, first run needs an allow in System Settings > Privacy & Security.
* Sign in to MakePlayingCards with an account created on their site directly --
  the automated browser cannot do a Google sign-in.

The XML points at absolute paths on this machine with `<sourceType>Local
File</sourceType>`, so nothing is uploaded to or fetched from Google Drive: the
desktop tool reads the PNGs straight off disk and uploads them to MPC. That
means the file is only good on the machine that generated it -- regenerate it
rather than copying it to another box.

The tool reads the available bracket sizes off the MPC page and picks the
smallest one the order fits. You pay by bracket, not by card, so the eight
agendas are not free: 84 cards fit MPC's 90 bracket and 92 push into the next
one up. If that matters more than having the agendas printed, `--no-agendas`
takes them out and writes the eight conditions on index cards instead.

When it finishes, it leaves you in the MPC cart with the project saved. **Check
the preview before paying** -- that is the last point at which a cropping
mistake is free.

## Card geometry

MakePlayingCards' standard poker card, which is what these numbers are:

| | Inches | mm | Pixels at 600 DPI |
|---|---|---|---|
| With bleed (what we render) | 2.72 x 3.70 | 69 x 94 | 1632 x 2220 |
| Trimmed (what you hold) | 2.48 x 3.46 | 63 x 88 | 1488 x 2076 |
| Safe area (nothing important outside it) | 2.32 x 3.30 | 59 x 84 | 1392 x 1980 |

## The border

The cut wanders by a millimetre or so in any direction, and the border is what
absorbs it. It is drawn from the bleed edge inwards over 0.22 in, so the trim
lands *inside* the border and takes 0.12 in off: what you hold has roughly a
0.10 in (2.5 mm) border, about what a Magic card carries. A millimetre of drift
changes that width by a millimetre, which nobody notices. The same millimetre
against a thin keyline set in from the trim is glaring -- one edge fat, the
opposite edge thin -- which is why the border is thick and runs off the edge
rather than being a hairline in from it.

The art is fitted to the window inside the border rather than being run full
bleed and then covered over, so no part of an illustration disappears under the
frame.

Each estate borders in a darkened mix of ink and its own colour -- Church
indigo, Military wine, Merchant teal, Commons bronze, and plain ink for the
cards that belong to no estate -- so a hand sorts by edge alone. A gold keyline
marks the seam between border and art.

Text plates are translucent (`--panel-alpha`, 186 of 255 by default). The patch
of art under each one is blurred and dimmed before the parchment goes over it,
which is what lets the plate sit that far below opaque with the type still
crisp over both a bright sky and a dark interior.

MPC needs 300 DPI. The desktop tool works an image's DPI out from its height
(300 DPI per 1110 px) and downscales anything above 800 before upload, so the
default 600 is the useful ceiling in practice: it is what keeps the rules text
crisp, since the source art is only just above 300 DPI on its own.

## Options

| Flag | What it does |
|---|---|
| `--dpi 300` | Render smaller. 300 is MPC's floor; text gets chunky. |
| `--format jpg --quality 95` | ~10x smaller files, much faster to upload. |
| `--stock "(M31) Linen"` | Cardstock. Also `(S27) Smooth`, `(S30) Standard Smooth`, `(S33) Superior Smooth`, `(P10) Plastic`. |
| `--foil` | Foil fronts. Not available on plastic stock. |
| `--no-agendas` | Leave out the 8 agenda cards: 84 cards, one bracket cheaper. |
| `--panel-alpha 220` | Make the text plates more opaque (255) or more transparent (0). |
| `--outmaneuver-copies 3` | Match a deck built with `--outmaneuver-copies 3`. |
| `--only 26,44` | Re-render just those asset numbers, for iterating on layout. |
| `--font-dir ~/fonts` | Search somewhere else for a serif face first. |

The script uses whatever serif it can find -- DejaVu Serif, Liberation Serif,
Georgia, Times -- in that order. Drop a face you would rather have into a
directory and point `--font-dir` at it.

## What the box still does not contain

* **A d6.** Targeted Poisoning and Poisoning at the Feast need one.
* **Anything but the default rules on the agenda cards.** Four agendas are
  dealt and four stay in the fog for `Schismatic Event` to draw from; the
  conditions printed on them are the defaults in `succession/agendas.py`. A
  table running `--faith-seats 5` or any other variant should treat the print
  as wrong and play off `docs/RULES.md`. The agendas are also the one part of
  the deck with no art -- they are set type on parchment.
* **A board.** Seven seats, named in `docs/RULES.md`. Index cards work.

## Alternate art

Eight of the events were drawn twice (`..._00001_.png` and `..._00002_.png`).
The script takes the lower-numbered one and lists the alternates when it
finishes. To print the other, swap the two filenames -- the script picks by
variant number, not by content.
