# Developing Court of Succession

The simulator, the print tooling and the browser game, for anyone changing
them. Players want the [README](../README.md); the balance numbers are in
[BALANCE.md](BALANCE.md).

The simulator is stdlib only, Python 3.10+. It runs the same from a terminal
or from a chat code-execution sandbox — no install step, no packages to fetch.
(The one exception is the print tooling in `tools/`, which needs Pillow to draw
cards; nothing in `succession/` imports it.)

```bash
python -m succession demo --seed 42                    # watch one game, move by move
python -m succession run --games 1000 --out r.csv --summary
python -m succession run --games 20000 --jobs 8 --out r.db --format sqlite
python -m succession analyze r.csv other.csv           # pool logs and summarise
python -m succession play                              # take a seat against the bots
python -m unittest discover -s tests                   # rule, session, deal and print tests
```

Roughly 150 games/second single-threaded; `--jobs N` scales linearly.

## Layout

| File | What's in it |
|---|---|
| `succession/courtiers.py` | The 41-courtier attribute table (estate · faith · family · origin) |
| `succession/cards.py` | Every card, deck construction, and the event-effect table |
| `succession/enums.py` | Estates, faiths, families, origins, the six seats |
| `succession/state.py` | `Config` (every rules knob) and `GameState` (cheap to clone) |
| `succession/actions.py` | Legal-move generation, including hand-vs-promotion enforcement |
| `succession/engine.py` | Card resolution, the turn loop, win checking |
| `succession/agendas.py` | The eight agendas: win predicates and the bots' progress metric |
| `succession/bots.py` | Naive, greedy, and strategic bots |
| `succession/session.py` | A game that stops for human seats: prompts, player views, records |
| `succession/terminal.py` | The `play` command's front end |
| `succession/webapi.py` | The JSON calls the browser game makes into a session |
| `succession/logsink.py` | CSV and SQLite writers, one row per game |
| `succession/analysis.py` | Batch summary statistics |
| `succession/runner.py` | CLI (`run`, `analyze`, `demo`) |
| `tools/mpcfill.py` | Composes the print and web card renditions and the MPC Autofill order |
| `tools/gallery.py` | The web rendition's self-contained index page |
| `tools/cardlist.py` | Writes `docs/CARDS.md`, the deck as Markdown |
| `tools/boardsheet.py` | Lays the seat cards out as a print-at-home PDF |
| `tools/webbundle.py` | Zips `succession/` for the browser game to run under Pyodide |
| `web/` | The browser game: React on top of this package running in Pyodide |
| `web/public/cards/` | The game's card pictures and `manifest.json`, from `mpcfill.py --profile game` |
| `tools/fetch_art.py` | Fetches the card art from the `art` release into `assets/` (it is not in git) |
| `tools/make_art_prompts.py` | Generates the image prompts the art in `assets/` was made from |
| `tools/card_text.py` | What each card prints: type line and rules text |
| `docs/RULES.md` | **The rules as implemented, every assumption, and the open questions** |
| `docs/DEVELOPING.md` | This page |
| `docs/BALANCE.md` | What the batch runs found, and what each rules change did |
| `docs/EMBED.md` | Putting the browser game on another site |
| `docs/PRINTING.md` | Turning `assets/` into a deck you can order |
| `docs/CARDS.md` | **Every card, with its picture, attributes and rules text** |
| `art/` | The prompts, output names and negative prompt behind `assets/` |

Read [RULES.md](RULES.md) before changing anything — it lists what the brief left
open, what the code assumed, and which flag flips each assumption.

## Printing a deck

`assets/` holds an illustration for every card and the back -- once fetched.
The art is too big to keep in git (about 137 MB); it lives as files on the
repository's [`art` release](https://github.com/bobbymeyer/succession/releases/tag/art),
and `python tools/fetch_art.py` downloads whatever `assets/` is missing or holds
stale. New or re-painted art is uploaded to that release, named as
`art/filenames.txt` says; then run **Print deck release** from the Actions tab.
The art carries no
name, no attributes and no rules text, so `tools/mpcfill.py` composes those
over it and writes the XML order file that
[MPC Autofill](https://github.com/chilli-axe/mpc-autofill) feeds to
MakePlayingCards:

```bash
pip install pillow                       # the only dependency, and only for this
python tools/mpcfill.py                  # -> build/mpc (print) and build/web (browser)
python tools/mpcfill.py --profile all --zip --format jpg --quality 95
```

The second command builds everything: the print cards, the browsable gallery,
`docs/CARDS.md` with its thumbnails, and the downloadable zip. The zip is the
one artifact meant to leave this machine, so the order file inside it points at
`cards/...` relative to itself rather than at absolute paths — unzip it
anywhere and it still finds its cards.

Nobody has to build the zip by hand for the download link above:
`.github/workflows/print-deck.yml` builds it and publishes it as the latest
GitHub release whenever `main` changes anything printed on a card (the art, the
card text, the layout or the cards themselves), and it can be run from the
Actions tab at any time.

Two renditions of the same 87 cards -- the 79-card play deck plus the eight
agendas. **Print** is full bleed at 600 DPI with the MPC Autofill order file
beside it; **web** is the trimmed card at 744 px with a self-contained
`index.html` that shows the deck. Each card is composed once and the web one is
a trim and a downscale of the print one, so they cannot disagree.

The agendas are the one part with no art and are set as type on parchment. Each
estate takes a border in its own darkened colour so a hand sorts by edge, and
the text plates are translucent over the illustration.

The deck it prints is read out of `succession/cards.py`, so the cards on the
table are the cards the bots played. Art file `NN_...` goes to deck slot
`NN - 1` and its kind and slug are checked against the card, so a gap in the
numbering stops the build instead of shifting forty portraits by one seat.
`docs/PRINTING.md` has the rest: card geometry, cardstock, the agenda cards,
and what is still not in the box.

## Playing a seat

`python -m succession play` deals you in against one bot of each tier and
takes you through the game a question at a time: your move on your turn, and
your pick whenever an event asks the whole table to name a victim or discard.
`--players human,strategic,strategic` sets the table, `--seed` deals a
particular game, and every rules flag from `run` works here too.

`--record game.json` saves the game when it ends or you quit: the seed, the
rules, and each decision you made. `--replay game.json` plays it back to where
it stopped and hands you the next move -- which makes a bug report one small
file.

A record replays only under the rules it was played by, and only the current
rules are kept: every change of rules bumps `RECORD_VERSION` in
`succession/session.py`, and an older record is refused with a message rather
than replayed wrongly.

**Deals.** A game can start from a stacked deal (`succession/deal.py`)
instead of a pure shuffle: whose hand holds what, which agendas are dealt, the
next cards off the deck, who moves first. A new player's first game is the
deal named `first_game`. Tests set up the situation they need this way rather
than hunting for a seed that happens to produce it, so a change to the deck
cannot quietly move them. In the browser, `?deal=<JSON>` on the address deals
it for the next Play -- handy for sharing a situation.

The terminal is one front end on `succession/session.py`; the browser game is
the other. `GameSession` runs the same turn loop as
`play_game()`, so a human seat plays exactly the game a bot seat would, and
`view()` is the whole of what a seat is shown: the board, your own hand and
agenda, and other players' hand sizes.

## The browser game

`web/` is the same game in a browser. The page runs this very package under
[Pyodide](https://pyodide.org) (Python compiled to WebAssembly) in a Web
Worker, so the rules and bots in the browser are the ones in this checkout, not
a port of them. The page never works out a rule: it shows `session.view()`, and
builds a move by narrowing the engine's list of legal actions as you play:
click a card to pick it up (its choices appear above it, and whatever it can
target lights up), or drag it straight to where it goes -- the outer circle,
the discard pile, a courtier, a player, or for an outer courtier an empty seat.

```bash
cd web
npm install
npm run dev              # http://localhost:5173, rebuilt as you edit
npm run build            # web/dist: a static site, Pyodide included
npx playwright test      # whole games in Chromium, against the build, on a desktop, an iPhone and a Pixel screen
```

Both `dev` and `build` first copy Pyodide out of `node_modules` and zip
`succession/` into `web/public/`, so a change to the rules shows up on the next
build. The site uses relative paths throughout: it can be served from any
directory, or iframed into another page.

On a phone it lays out for one screen, upright or on its side: the board, with
a dock under your thumb for the question, your hand and the log. Tap a card to
pick it up, hold one to read it, or hold and drag. It can be added to a home
screen (`web/public/manifest.webmanifest`) and, once opened, plays offline:
`web/public/sw.js` keeps the page, Pyodide (under its version, so an upgrade
replaces it), the engine and the art, and phones draw 320px copies of the cards
(`web/public/cards/sm/`).

The cards on the table are the printed cards: `tools/mpcfill.py --profile game`
composes every card, agenda and seat exactly as the print deck does, trims and
shrinks them to 496px WebP (3.8 MB for all 100), and writes them with a
`manifest.json` into `web/public/cards/`. They are committed, like the
`docs/cards/` thumbnails, so building the site needs no Pillow; re-run the
profile after changing a card or its art, and `tests/test_game_cards.py` fails
until you do. A printed card shows printed attributes, so the page adds what
the table has done since: each courtier's live estate, faith, house and origin
under the card, changed ones in red, and any Defense they carry. Click any card
to see it full size. A courtier's details always sit in the same grid --
estate and faith above, house and origin (or a barbarian's people) below.

Your agenda is tracked clause by clause, in a tab beside the log under the
question you are being asked: which parts the
court meets right now, how far along the rest are, and who is waiting in the
outer circle to help (`conditions()` in `succession/agendas.py`; all of them
met is exactly the win).

Cards move the way they would on a table: a card played from your hand glides
to where it lands, a bot's card flies out of that bot's place, and whatever
just moved glows for a moment. The bot speed setting paces it (Instant turns
it off, as does the system's reduced-motion setting).

**Human games are playtest data.** Every finished game is kept in the browser
as its record -- seed, rules, and each decision -- and "Download games as CSV"
replays them through the simulator and writes the same log `run` does, one row
per game, with `human` as a tier:

```bash
python -m succession analyze games.csv              # humans beside the bots
python -m succession analyze games.csv batch.csv    # or pooled with a batch run
```

A log may mix table sizes; seats a smaller table did not have are left blank.
The end-of-game screen also copies or downloads the one game's record, which
`python -m succession play --replay` or the page's "Load a saved game" plays
back move for move.

**Published from `main`.** `.github/workflows/pages.yml` runs the simulator
tests (on Python 3.10 and 3.14, the one Pyodide uses) and the browser tests on
every push, and on `main` publishes `web/dist` to
<https://bobbymeyer.github.io/succession/>. [docs/EMBED.md](EMBED.md) has
the iframe snippet for putting it on another page, and the two Netlify lines
that serve it at bobbymeyer.com/succession/ instead.

## The bots

All three see only public information plus their own agenda.

* **Naive** — a uniformly random legal action.
* **Greedy** — one-ply lookahead, maximising progress on its own hidden agenda
  and ignoring everyone else.
* **Strategic** — maximises its own agenda *minus* a threat term over the whole
  seven-agenda pool, so it disrupts boards that drift toward any win condition,
  known to it or not. It also keeps a belief model: each opponent's actions are
  scored against every agenda, and the agendas an opponent's play keeps
  advancing get weighted up. That belief is what picks the Outmaneuver target.

Add a tier by subclassing `bots.Bot` and registering it in `BOT_TIERS`.

## The log

One row per game. Key columns: `turns`, `rounds`, `timeout`, `num_winners`,
`double_win`, `winning_agendas`, `winning_tiers`, `reshuffles`, per-player
`p{n}_tier` / `p{n}_agenda` / `p{n}_won`, the six `seat_*` occupants, the final
inner-circle composition (`inner_amonides`, `inner_old_gods`, …), and per-kind
card-play counters. That is enough for agenda win-rate distribution, double-win
frequency, game length, and tier suppression without re-running anything.

`analyze` takes several logs at once, which is how the suppression comparison
works: run one batch with a strategic seat and one without, then pool them.
