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
| `succession/courtiers.py` | The 40-courtier attribute table (estate · faith · family · origin) |
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

6,000 games, default mix (`naive, greedy, strategic, naive`, seats shuffled):

```
Game length: mean 40.8 player-turns (10.6 rounds), median 37, max 149
Double wins: 7.1%          Timeouts: 0%

Win rate by tier      naive 13.0%   greedy 24.6%   strategic 56.6%

Win rate by agenda    Balance                         41.2%
                      Faith Ascendant: Mystery Cults  34.5%
                      Faith Ascendant: Old Gods       33.8%
                      Barbarian Conquest              27.8%
                      House Rising: Amonides          17.9%
                      House Rising: Argaian           15.7%
                      House Rising: Mitreas           15.7%
```

1. **The seven agendas span 16–41%**, against 2–53% under the first draft of
   the rules. The faiths are within 0.7 of each other and the houses within
   2.2.

2. **The charioteers moved the houses up about two points** (from ~15 to ~16–18)
   by opening the Guildmaster's seat to them — it was the one seat no house
   could ever hold.

3. **The tiers separate cleanly**, which is the sanity check that the bots are
   really playing the game: 13.0% → 24.6% → 56.6%. A strategic bot at the table
   also suppresses everyone else. Swapping exactly one greedy seat for a
   strategic seat (6,000 games each, everything else held fixed):

   | | other three players' win rate | mean game length |
   |---|---|---|
   | without a strategic bot | 26.9% | 29.4 turns |
   | with a strategic bot | 16.8% | 40.8 turns |

Games always resolve: no timeouts in 24,000 games at the 600-turn cap.

### Balance's seat threshold is a very light touch at five

`--balance-seats` sets how full the court must be before Balance counts. Five
was meant to stop it being satisfied by accident, but the board already
averages 5.27 filled seats when someone wins, so the requirement is usually
already true. 6,000 games each:

| Threshold | Balance | naive wins Balance | mean turns |
|---|---|---|---|
| 4 of 7 | 41.5% | 26.1% | 40.2 |
| **5 of 7 (current)** | **41.2%** | **25.4%** | 40.8 |
| 6 of 7 | 35.3% | 21.5% | 42.6 |
| 7 of 7 | 24.3% | 12.4% | 44.6 |

The naive column is the one that matters. Balance is the agenda a player
can win without meaning to — a bot playing at random wins it a quarter of the
time, against 13–17% on the faiths and Conquest and 6% on a house. Five of
seven barely touches that. Seven of seven brings it into line with everything
else, at the cost of making Balance the weakest agenda on the board; six is the
middle.

### Faith parity is about benches, not head count

The charioteers are one Commons courtier per house, and adding them quietly
cost Old Gods 3.8 points against Mystery Cults across three separate 6,000-game
runs. Head count was level at 18/18 the whole time. The cause was the shape of
the benches:

| | Church | Military | Merchant | Commons |
|---|---|---|---|---|
| Old Gods | 5 | 5 | **3** | 5 |
| Mystery Cults | 3 | 7 | 6 | 2 |

Seats run Church 2, Military 2, Merchant 2, Commons 1. Mystery Cults had 13
courtiers for the four Military and Merchant seats; Old Gods had 8, with only
three Merchant courtiers for two seats — the thinnest pool on the board — and
five commoners queuing for a single seat. Moving *Uncrowned Victor* to Old Gods
(Argaian is the mixed-faith house, so it can carry either) and paying for it
with *Fastest of the Games* closes the gap from 3.8 points to 0.6 without
changing a single head count.

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

## What still needs you

`docs/RULES.md` ends with the open questions. Two of them matter.

**How many seats should a faith need?** Four was two-thirds of a six-seat
board and is a bare majority of seven, which is why the faiths lead the table.
`--faith-seats 5` restores the two-thirds shape; both sets of numbers are in
`docs/RULES.md`. It is the one threshold the seventh seat changed the meaning
of without anyone deciding to.

**Event effects.** The bigger one. The brief called out that the source
document's effects were written for the board-wide version and do not map onto
single-target. The ten events currently use a playable placeholder table (all
in one place in `cards.py`), but three of them duplicate "target leaves play",
and `Treasure Fleet` is implemented as a *helpful* event — both worth a
decision before the balance numbers above mean much.
