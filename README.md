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
Game length: mean 44.6 player-turns (11.5 rounds), median 42, max 167
Double wins: 9.6%          Timeouts: 0%

Win rate by tier      naive 13.5%   greedy 24.9%   strategic 57.8%

Win rate by agenda    Faith Ascendant: Mystery Cults  40.0%
                      Faith Ascendant: Old Gods       38.5%
                      Barbarian Conquest              31.5%
                      Balance                         24.1%
                      House Rising: Amonides          20.5%
                      House Rising: Argaian           18.9%
                      House Rising: Mitreas           18.7%
```

1. **The seven agendas span 19–40%**, against 2–53% under the first draft of
   the rules. The faiths are within 1.5 points of each other and the houses
   within 1.8.

2. **Balance is no longer the agenda you win by accident.** At the full seven
   seats a bot playing at random wins it 12.7% of the time, against 25.5% when
   it only needed five — in line with the houses now, and below the faiths.

3. **Double wins are up to 9.6%**, from 7.1% at five seats. A court full enough
   to satisfy Balance is usually full enough to hand somebody a faith as well,
   so the two agendas land together more often.

4. **The tiers separate cleanly**, which is the sanity check that the bots are
   really playing the game: 13.5% → 24.9% → 57.8%. A strategic bot at the table
   also suppresses everyone else. Swapping exactly one greedy seat for a
   strategic seat (6,000 games each, everything else held fixed):

   | | other three players' win rate | mean game length |
   |---|---|---|
   | without a strategic bot | 27.4% | 31.8 turns |
   | with a strategic bot | 17.3% | 44.6 turns |

Games always resolve: no timeouts in 24,000 games at the 600-turn cap.

### What the Balance threshold buys

`--balance-seats` sets how full the court must be before Balance counts. The
board averages 5.3 filled seats at a win, so anything up to five is a rule that
is usually already true. 6,000 games each:

| Threshold | Balance | naive wins Balance | mean turns | double wins |
|---|---|---|---|---|
| 4 of 7 | 42.4% | 26.2% | 40.1 | 6.8% |
| 5 of 7 | 41.2% | 25.5% | 40.8 | 7.1% |
| 6 of 7 | 36.0% | 21.8% | 42.6 | 8.7% |
| **7 of 7 (current)** | **24.1%** | **12.7%** | 44.6 | 9.6% |

The middle column is the one that matters: it is how often a player who is not
trying wins Balance. Only the full seven brings that into line with the rest of
the board.

It also inverts what kind of agenda Balance is. At five seats it was easy to
stumble into and nearly impossible to deny, since any seat anybody filled might
complete it. At seven it is the hardest agenda on the board for the strategic
bot too — 50.2%, against 63% for Conquest and 76% for the faiths — because a
full court takes real work to assemble and one removal anywhere undoes it.

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
