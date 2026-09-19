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
Game length: mean 41.5 player-turns (10.7 rounds), median 38, max 199
Double wins: 6.6%          Timeouts: 0%

Win rate by tier      naive 13.0%   greedy 24.9%   strategic 55.8%

Win rate by agenda    Balance                         40.2%
                      Faith Ascendant: Old Gods       34.8%
                      Faith Ascendant: Mystery Cults  32.7%
                      Barbarian Conquest              31.0%
                      House Rising: Amonides          17.1%
                      House Rising: Mitreas           15.6%
                      House Rising: Argaian           14.4%
```

1. **The seven agendas span 14–40%**, against 2–53% under the first draft of
   the rules. The two faiths and Conquest sit within four points of each other,
   and the three houses within 2.7.

2. **The two faiths are at parity.** Old Gods leads by 2.0 here; in an
   independent 8,000-game batch on a different seed Mystery Cults led by 1.8.
   The sign flips, which is what parity looks like.

3. **Balance still leads by five points.** It is the agenda godlessness cannot
   touch — it only ever needed *one* seat of each faith, so a godless courtier
   costs it nothing, while both Faith Ascendants lose a candidate outright.

4. **The tiers separate cleanly**, which is the sanity check that the bots are
   really playing the game: 13.0% → 24.9% → 55.8%. A strategic bot at the table
   also suppresses everyone else. Swapping exactly one greedy seat for a
   strategic seat (4,000 games each, everything else held fixed):

   | | other three players' win rate | mean game length |
   |---|---|---|
   | without a strategic bot | 26.9% | 29.4 turns |
   | with a strategic bot | 17.0% | 41.5 turns |

   It takes about a third of the other players' equity and makes games ~40%
   longer — it is genuinely denying wins, not just winning faster.

Games always resolve: no timeouts in 16,000 games at the 600-turn cap.

### Which courtiers turn Godless decides whether the faiths are level

With 37 courtiers the Godless count has to be odd for the two faiths to come
out even, so three is the smallest useful number — and two of the three have to
come out of Old Gods. *Which* two settles it. Old Gods' surplus is six Commons
courtiers competing for a single seat; its Church, Military and Merchant
benches are what actually win it seats. Ten trios, 8,000 games each, gap in
percentage points between the two Faith Ascendant win rates:

| Both Old Gods conversions taken from... | gap |
|---|---|
| Commons (current: Ten Thousand Verses, Master Swordsmith) | **1.8** |
| one Commons, one house courtier | 3.8 – 4.7 |
| one per house — both from Church/Military/Merchant | 4.1 – 5.8 |

So "one from each house" costs about four points of faith imbalance, because
house courtiers all sit in the estates Old Gods cannot spare. The current trio
instead spends its dead weight, and the price is that only one house (Mitreas)
has a godless courtier. One line in `courtiers.py` either way.

### Balance is the game's equalizer

`--drop-agendas balance` answers what the game looks like without it (6,000
games each, everything else held fixed):

| | naive | greedy | strategic | mean turns | agenda spread |
|---|---|---|---|---|---|
| all seven agendas | 13.0% | 24.9% | 55.8% | 41.5 | 14.4–40.2% |
| without Balance | 11.0% | 21.4% | **64.5%** | 45.6 | 17.3–37.7% |
| control: without a *house* agenda | 13.2% | 25.0% | 55.9% | 40.1 | — |

The control matters: dropping any agenda leaves six in the pool and two in the
fog, but dropping a house agenda changes nothing. It is Balance specifically.

Two things happen at once. The agendas that remain tidy up — the spread
narrows to 17–38% and sorts cleanly into faiths, then Conquest, then the
houses within 1.3 points of each other — and the skill gap widens sharply,
because Balance is the one agenda a player can win without meaning to. Win
rate per deal, with Balance in the game:

| Agenda | naive | greedy | strategic |
|---|---|---|---|
| **Balance** | **26.1%** | 36.4% | 71.8% |
| Barbarian Conquest | 13.5% | 34.2% | 64.5% |
| Faith Ascendant (mean) | 17.4% | 30.8% | 66.2% |
| House Rising (mean) | 5.8% | 13.2% | 39.4% |

A bot playing at random wins Balance a quarter of the time — one and a half
times its rate on the next-best agenda and four times its rate on a house. It
is also the hardest agenda to *deny*, because it is satisfied by a diverse
board, so almost any seat someone fills can complete it. Take it out and the
strategic bot stops spending turns defending against a threat it cannot
block, which is most of the jump from 56% to 64%.

So it is a design question rather than a balance bug: Balance is what keeps a
four-player game from being won two times in three by whoever plans best.

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
