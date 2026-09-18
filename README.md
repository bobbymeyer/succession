# Court of Succession — headless simulator

A dependency-free Python simulator for the card-driven succession game: full
card and board model, a rules engine, three tiers of bot, and a CLI that runs
N games and logs each one to CSV or SQLite for balance analysis.

Stdlib only, Python 3.10+. It runs the same from a terminal or from a chat
code-execution sandbox — no install step, no packages to fetch.

```bash
python -m succession demo --seed 42                    # watch one game, move by move
python -m succession run --games 1000 --out r.csv --summary
python -m succession run --games 20000 --jobs 8 --out r.db --format sqlite
python -m succession analyze r.csv other.csv           # pool logs and summarise
python -m unittest discover -s tests                   # 47 rule tests
```

Roughly 150 games/second single-threaded; `--jobs N` scales linearly.

## Layout

| File | What's in it |
|---|---|
| `succession/courtiers.py` | The 34-courtier attribute table (estate · faith · family · origin) |
| `succession/cards.py` | Every card, deck construction, and the event-effect table |
| `succession/enums.py` | Estates, faiths, families, origins, the six seats |
| `succession/state.py` | `Config` (every rules knob) and `GameState` (cheap to clone) |
| `succession/actions.py` | Legal-move generation, including hand-vs-promotion enforcement |
| `succession/engine.py` | Card resolution, the turn loop, win checking |
| `succession/agendas.py` | The seven agendas: win predicates and the bots' progress metric |
| `succession/bots.py` | Naive, greedy, and strategic bots |
| `succession/logsink.py` | CSV and SQLite writers, one row per game |
| `succession/analysis.py` | Batch summary statistics |
| `succession/runner.py` | CLI (`run`, `analyze`, `demo`) |
| `docs/RULES.md` | **The rules as implemented, every assumption, and the open questions** |

Read `docs/RULES.md` before changing anything — it lists what the brief left
open, what the code assumed, and which flag flips each assumption.

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

4,000 games, default mix (`naive, greedy, strategic, naive`, seats shuffled):

```
Game length: mean 49.1 player-turns (12.6 rounds), median 44, max 236
Double wins: 3.2%          Timeouts: 0%

Win rate by tier      naive 15.6%   greedy 23.2%   strategic 48.9%

Win rate by agenda    Conquest                        53.3%
                      Faith Ascendant: Old Gods       39.8%
                      Balance                         38.9%
                      Faith Ascendant: Mystery Cults  38.2%
                      House Rising: Amonides           2.4%
                      House Rising: Argaian            2.3%
                      House Rising: Mitreas            1.9%
```

Three things fall out of that, all worth a design conversation:

1. **House Rising is close to unwinnable — ~2% against ~40% for the others.**
   It is the only agenda needing four *specific* courtiers seated at once, and
   estate coverage makes even that hard: each house has 2 Church, 2 Military
   and 2 Merchant courtiers and *no* commoner, so it can reach at most five of
   the six seats, and every rival can undo a seat with one card. Options: drop
   the threshold to 3 seats, count a house's outer-circle courtiers, or let a
   house claim the Guildmaster seat.

2. **Conquest is the easiest agenda, and it is the "anywhere in play" clause
   doing it** — three barbarians merely need to be on the table, including in
   the outer circle, and the two Military seats fill up on their own. Running
   with `--strict-conquest` (both Military seats held *by barbarians*) over
   3,000 games moves it from 53% to 24% and puts it below the two faith
   agendas, which looks much healthier.

3. **The tiers separate cleanly**, which is the sanity check that the bots are
   really playing the game: 15.6% → 23.2% → 48.9%. A strategic bot at the table
   also suppresses everyone else. Swapping exactly one greedy seat for a
   strategic seat (4,000 games each, everything else held fixed):

   | | other three players' win rate | mean game length |
   |---|---|---|
   | without a strategic bot | 25.9% | 33.4 turns |
   | with a strategic bot | 18.1% | 49.1 turns |

   It takes about a third of the other players' equity and makes games ~47%
   longer — it is genuinely denying wins, not just winning faster.

Games always resolve: no timeouts in 15,000 games at the 600-turn cap.

## What still needs you

`docs/RULES.md` ends with the open questions. The big one is the **event
effects**: the brief called out that the source document's effects were written
for the board-wide version and do not map onto single-target. The ten events
currently use a playable placeholder table (all in one place in `cards.py`),
but three of them duplicate "target leaves play", and `Treasure Fleet` is
implemented as a *helpful* event — both worth a decision before the balance
numbers above mean much.
