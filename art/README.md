# Art

Where the illustrations in `assets/` come from.

| File | What it is |
|---|---|
| `prompts.txt` | One image prompt per card, 84 lines |
| `filenames.txt` | The output name for each, same order |
| `negative.txt` | One negative prompt, shared by every card |

All three are generated, not written by hand:

```bash
python tools/make_art_prompts.py
```

The two long files are line-aligned on purpose: a batch run that reads line N
from each lands prompt N on filename N. The negative is a single line because
every card shares it — if your loader wants one negative per positive, repeat
it:

```bash
yes "$(cat art/negative.txt)" | head -n $(wc -l < art/prompts.txt) > batch.txt
```

## The recipe

Every card gets two on-flavour Hellenistic details, two fantasy details and one
surreal element, wrapped in framing that depends on the kind: courtiers are
portraits, action cards show two figures interacting, events are spectacle. The
world is Hellenistic Greece and the successor kingdoms — Macedonian, Seleucid,
Ptolemaic, Thracian, Scythian, Persian, Egyptian. Explicitly not Roman, not
medieval, not modern.

Nothing a prompt does *not* want is named in the prompt. Every exclusion lives
in `negative.txt` instead, so no positive prompt ever mentions a toga in order
to ask for its absence.

## Why the filenames matter

`filenames.txt` is where the naming in `assets/` comes from, and
`tools/assets.py` checks each asset's number, kind and slug against the card at
that deck slot before composing anything. The two have to agree or the deck
will not build. `tests/test_card_text.py` pins the generator against the
committed files, and the committed files against the art on disk.

Adding a card means adding its entry to `DETAILS` in
`tools/make_art_prompts.py`; the generator exits naming any card it has no
details for rather than writing a prompt without them.
