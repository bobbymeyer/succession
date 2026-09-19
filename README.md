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
| `succession/courtiers.py` | The 37-courtier attribute table (estate · faith · family · origin) |
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
Game length: mean 43.1 player-turns (11.1 rounds), median 39, max 189
Double wins: 5.7%          Timeouts: 0%

Win rate by tier      naive 12.9%   greedy 23.9%   strategic 56.1%

Win rate by agenda    Balance                         42.3%
                      Faith Ascendant: Mystery Cults  31.7%
                      Barbarian Conquest              30.9%
                      Faith Ascendant: Old Gods       30.8%
                      House Rising: Amonides          17.1%
                      House Rising: Argaian           15.7%
                      House Rising: Mitreas           15.4%
```

1. **The seven agendas span 15–42%**, against 2–53% under the first draft of
   the rules. The two faiths and Conquest are within a point of each other, and
   the three houses within 1.7.

2. **Balance is now the outlier at the top**, 10 points clear. Atheism is why:
   the two faith agendas each lost ~8 points when five courtiers stopped
   counting for them, but Balance only ever needed *one* seat of each faith, so
   it barely noticed — and it gained from its rivals slowing down.

3. **The houses climbed to 15–17%** for the same reason, without being touched.
   They were the floor of the board at ~11% two changes ago.

4. **The faiths are within a point of each other** (31.7% / 30.8%) on a 16/16
   roster. That took some care in *which* courtiers turned atheist — see below.

5. **The tiers separate cleanly**, which is the sanity check that the bots are
   really playing the game: 12.9% → 23.9% → 56.1%. A strategic bot at the table
   also suppresses everyone else. Swapping exactly one greedy seat for a
   strategic seat (4,000 games each, everything else held fixed):

   | | other three players' win rate | mean game length |
   |---|---|---|
   | without a strategic bot | 26.5% | 30.4 turns |
   | with a strategic bot | 16.6% | 43.1 turns |

   It takes about a third of the other players' equity and makes games ~40%
   longer — it is genuinely denying wins, not just winning faster.

Games always resolve: no timeouts in 16,000 games at the 600-turn cap.

### Apostasy is the first card only one tier will play

Apostasy can never advance your own agenda — it only takes a seat away from
someone else's. That makes it a clean separator, and the bots split exactly as
their definitions say they should (4,000 games, counting real plays only, not
the lookahead the thinking bots do internally):

| Tier | Played | Discarded | |
|---|---|---|---|
| naive | 876 | 322 | 73% — it is picking at random |
| greedy | **0** | 52 | 0% — advancing nobody's agenda, so never worth a turn |
| strategic | 467 | 35 | 93% — almost always worth a turn |

Its effect on the board is smaller than the reassignment that created the
atheists. Taking the card out of the deck entirely and keeping the five
atheist courtiers moves the faiths by about a point (31.7% → 32.6% and 30.8% →
31.9%) and shortens games from 43.1 to 41.9 turns. Barbarian Conquest is what
actually depends on it, gaining two points (28.8% → 30.9%) from the room the
card takes out of the faiths' schedule.

### Which courtiers turn atheist matters more than how many

The five atheists have to come out of the faiths unevenly — three Old Gods and
two Mystery Cults, to land on 16/16 — and the obvious picks put the faiths 3.9
points apart. Old Gods' depth sits in Commons, which has one seat, so its
Church and Military courtiers are worth far more to it than its commoners are.
Taking the Old Gods losses from Commons instead closes the gap (3,000 games
each):

| Atheist set | Old Gods | Mystery Cults | gap |
|---|---|---|---|
| Sword of the Assembly (Church), Mender, Blade for Any Banner | 27.9% | 31.8% | 3.9 |
| **Horse Breaker, Master Swordsmith, Mender** (current) | **31.2%** | **32.3%** | **1.2** |

The flavour cost is real: *Blade for Any Banner* is the best atheist name on
the roster and it is back to Mystery Cults. One line in `courtiers.py` if you
want it the other way.

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
