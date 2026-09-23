# Court of Succession — playtest alpha

A dependency-free Python simulator for the card-driven succession game: full
card and board model, a rules engine, three tiers of bot, and a CLI that runs
N games and logs each one to CSV or SQLite for balance analysis.

**[The deck](docs/CARDS.md)** — all 92 cards as images, with every courtier's
printed attributes and every action card's rules text.
**[Download the print-ready deck](https://github.com/bobbymeyer/succession/releases/latest/download/succession-print-deck.zip)**
— the card images plus the MPC Autofill order file, sized and bled the way
MakePlayingCards wants them. Unzip it anywhere, drop the `autofill` executable
beside `succession.xml`, run it, and it fills the order for you;
[docs/PRINTING.md](docs/PRINTING.md) has the detail. Not ordering anything?
The board prints at home: [A4](docs/board-a4.pdf) or
[Letter](docs/board-letter.pdf), two pages, cut out the seven seats.

**Playtest alpha.** The rules are settled enough to put in front of players:
every agenda is winnable, the eight of them sit inside seven points of each
other, and 24,000 simulated games resolve without a single stall. What is
alpha about it is that none of it has been played by a human yet — the numbers
come from bots, and the open questions in `docs/RULES.md` are the ones a table
will answer faster than a batch run.

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
python -m unittest discover -s tests                   # 140 rule, session and print tests
```

Roughly 150 games/second single-threaded; `--jobs N` scales linearly.

## Layout

| File | What's in it |
|---|---|
| `succession/courtiers.py` | The 40-courtier attribute table (estate · faith · family · origin) |
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
| `tools/make_art_prompts.py` | Generates the image prompts the art in `assets/` was made from |
| `tools/card_text.py` | What each card prints: type line and rules text |
| `docs/RULES.md` | **The rules as implemented, every assumption, and the open questions** |
| `docs/EMBED.md` | Putting the browser game on another site |
| `docs/PRINTING.md` | Turning `assets/` into a deck you can order |
| `docs/CARDS.md` | **Every card, with its picture, attributes and rules text** |
| `art/` | The prompts, output names and negative prompt behind `assets/` |

Read `docs/RULES.md` before changing anything — it lists what the brief left
open, what the code assumed, and which flag flips each assumption.

## Printing a deck

`assets/` holds an illustration for every card and the back. The art carries no
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

Two renditions of the same 92 cards -- the 84-card play deck plus the eight
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
builds a move by narrowing the engine's list of legal actions as you click.

```bash
cd web
npm install
npm run dev              # http://localhost:5173, rebuilt as you edit
npm run build            # web/dist: a static site, Pyodide included
npx playwright test      # whole games in Chromium, against the build
```

Both `dev` and `build` first copy Pyodide out of `node_modules` and zip
`succession/` into `web/public/`, so a change to the rules shows up on the next
build. The site uses relative paths throughout: it can be served from any
directory, or iframed into another page.

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
<https://bobbymeyer.github.io/succession/>. [docs/EMBED.md](docs/EMBED.md) has
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

## First findings

6,000 games, default mix (`naive, greedy, strategic, naive`, seats shuffled):

```
Game length: mean 53.6 player-turns (13.8 rounds), median 47, max 233
Double wins: 6.5%          Timeouts: 0%

Win rate by tier      naive 10.5%   greedy 27.0%   strategic 58.4%

Win rate by agenda    Barbarian Conquest              31.6%
                      House Rising: Amonides          27.1%
                      House Rising: Mitreas           26.4%
                      Balance                         26.0%
                      Faith Ascendant: Mystery Cults  25.7%
                      Faith Ascendant: The One God    25.7%
                      House Rising: Argaian           25.4%
                      Faith Ascendant: Old Gods       25.1%
```

1. **All eight agendas sit inside 6.5 points**, from 25.1% to 31.6%, against
   2–53% under the first draft of the rules. The three faiths finish within 0.6
   points of each other and the three houses within 1.7.

2. **Table-wide events narrowed the skill gap rather than widening it.** The
   strategic bot came down from 62.0% to 58.5% and the greedy bot rose from
   23.2% to 26.2%. Events that hit everybody — a purge that kills four
   courtiers at once, a freeze that protects whoever is ahead, a redeal that
   throws away everyone's plans — disrupt a carefully built position as much as
   a careless one. The single-target version they replaced rewarded the player
   tracking the whole board; these do not.

3. **Events are played about twice a game**, down from four times when they
   were single-target. Four of the five pairs advance nobody's agenda directly,
   so they are held for the turn they matter rather than spent on sight.

   Suppression, swapping exactly one greedy seat for a strategic one (6,000
   games each):

   | | other three players' win rate | mean game length |
   |---|---|---|
   | without a strategic bot | 26.6% | 41.5 turns |
   | with a strategic bot | 16.0% | 53.6 turns |

Games always resolve: no timeouts in 24,000 games at the 600-turn cap.

### One cynic makes the faiths divide evenly

Forty courtiers do not divide by three. Exactly one is born Godless — the Dog
of the Agora, a barefoot street philosopher who sleeps in a wine jar — and
taking him off the top leaves thirty-nine, so the three faiths get thirteen
each with an identical bench in every estate:

| | Church | Military | Merchant | Commons |
|---|---|---|---|---|
| Old Gods | 3 | 4 | 3 | 3 |
| Mystery Cults | 3 | 4 | 3 | 3 |
| The One God | 3 | 4 | 3 | 3 |
| The Dog of the Agora | — | — | — | 1 |

It is worth doing. At 14 / 13 / 13 the faith holding the odd card led the other
two by about a point and a half, and the lead moved when the card did. At
13 / 13 / 13 they finish within 1.2 points. Everyone else reaches godlessness
the hard way, through Apostasy.

### What the Balance threshold buys

`--balance-seats` sets how full the court must be before Balance counts. Six is
the default: one empty chair is allowed, a second is not.

Seven was the default for a while, chosen to stop a careless player falling
into Balance by accident. That premise rested on a blind spot — the bots were
badly under-using purges and freezes, so courts filled up more than they should
have. Once the events were priced properly, a full court became rare enough
that Balance dropped to 20.8%, five points clear of anything else at the
bottom, and the spread across the eight agendas blew out to 13 points.

6,000 games each, on the corrected bots:

| Threshold | Balance | naive wins Balance | spread across all eight |
|---|---|---|---|
| **6 of 7 (current)** | **26.0%** | 13.0% | **6.5 points** |
| 7 of 7 | 20.8% | 9.7% | 13.0 points |

The accident problem does not come back at six. The naive bot's overall win
rate is 10.5%, so winning Balance 13.0% of the time is barely above its own
average — nothing like the 25.5% that made the change worth doing in the first
place.

### Apostasy is the first card only one tier will play

Apostasy can never advance your own agenda — it only takes a seat away from
someone else's. The bots split exactly as their definitions say they should
(4,000 games, counting real plays, not the lookahead the thinking bots run):

| Tier | Played | Discarded | |
|---|---|---|---|
| naive | 876 | 322 | 73% — it is picking at random |
| greedy | **0** | 52 | 0% — advancing nobody's agenda, so never worth a turn |
| strategic | 467 | 35 | 93% — almost always worth a turn |

### Variants already wired up

| Flag | Effect on the batch |
|---|---|
| `--faith-seats 5` | faiths drop ~20 points; Balance and Conquest take the lead |
| `--house-any-three` | drops the own-estate requirement |
| `--house-preferred-estates mitreas=church` | reassign a house's own estate |
| `--removed-out-of-game` | killed courtiers never return |
| `--defense-matches-target` | an estate Defense may only shield its own estate |
