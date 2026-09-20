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
    succession.xml                     the order file
```

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
smallest one the order fits, so 84 cards land in MPC's 90-card bracket. The six
spare slots cost the same as the deck does; `--include-agendas` fills eight of
them with the agenda cards and pushes the order into the next bracket up.

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

The cut wanders by a millimetre or so, which is why the title and text plates
sit 0.20 in inside the bleed edge and why there is no frame around the card --
a keyline that close to the trim shows every wobble, a full-bleed illustration
shows none.

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
| `--include-agendas` | Add the 8 agenda cards. They are text-only -- no art was drawn for them. |
| `--outmaneuver-copies 3` | Match a deck built with `--outmaneuver-copies 3`. |
| `--only 26,44` | Re-render just those asset numbers, for iterating on layout. |
| `--font-dir ~/fonts` | Search somewhere else for a serif face first. |

The script uses whatever serif it can find -- DejaVu Serif, Liberation Serif,
Georgia, Times -- in that order. Drop a face you would rather have into a
directory and point `--font-dir` at it.

## What the box still does not contain

* **A d6.** Targeted Poisoning and Poisoning at the Feast need one.
* **Agenda cards**, unless you pass `--include-agendas`. Eight agendas, four
  dealt and four left in the fog for `Schismatic Event` to draw from. The
  printed conditions are the defaults in `succession/agendas.py`; a table
  running `--faith-seats 5` or any other variant should treat the print as
  wrong and play off `docs/RULES.md`.
* **A board.** Seven seats, named in `docs/RULES.md`. Index cards work.

## Alternate art

Eight of the events were drawn twice (`..._00001_.png` and `..._00002_.png`).
The script takes the lower-numbered one and lists the alternates when it
finishes. To print the other, swap the two filenames -- the script picks by
variant number, not by content.
