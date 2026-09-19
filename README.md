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
| `succession/agendas.py` | The eight agendas: win predicates and the bots' progress metric |
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
Game length: mean 57.3 player-turns (14.7 rounds), median 52, max 351
Double wins: 6.1%          Timeouts: 0%

Win rate by tier      naive 10.5%   greedy 23.2%   strategic 62.0%

Win rate by agenda    Barbarian Conquest              30.1%
                      House Rising: Mitreas           28.1%
                      House Rising: Amonides          26.8%
                      Faith Ascendant: The One God    26.3%
                      House Rising: Argaian           26.2%
                      Balance                         25.1%
                      Faith Ascendant: Old Gods       24.9%
                      Faith Ascendant: Mystery Cults  24.8%
```

1. **All eight agendas sit inside 5.2 points**, from 24.8% to 30.1%, against
   2–53% under the first draft of the rules. Nothing is obviously the best or
   worst thing to be dealt.

2. **The event rewrite tightened it further than the agenda tuning did** — 8.7
   points to 5.2 — and lifted the faiths about two points. Replacing three
   duplicate "target leaves play" events with attribute damage (Famine strips a
   family, Meteor ruins an estate) means fewer courtiers get killed outright
   (2.4 per game, down from 3.3), boards stay fuller (6.01 of 7 seats at the
   end), and the pressure lands on what a courtier *is* rather than on whether
   they are there at all.

3. **The skill premium is the open worry.** The strategic bot has climbed 57.9%
   → 60.9% → 62.0% over the last two changes, while the naive bot has fallen to
   10.5%. Every constraint added to an agenda, and every event that damages an
   attribute rather than clearing a seat, rewards the player tracking the whole
   board. It is worth deciding what spread between a thinking player and a
   careless one the game wants.

   Suppression, swapping exactly one greedy seat for a strategic one (6,000
   games each):

   | | other three players' win rate | mean game length |
   |---|---|---|
   | without a strategic bot | 26.5% | 43.0 turns |
   | with a strategic bot | 14.7% | 57.3 turns |

Games always resolve: no timeouts in 24,000 games at the 600-turn cap.

### Every faith gets the same bench

Three faiths at twelve courtiers each, with identical estate spreads:

| | Church | Military | Merchant | Commons |
|---|---|---|---|---|
| Old Gods | 3 | 4 | 3 | 2 |
| Mystery Cults | 3 | 4 | 3 | 2 |
| The One God | 3 | 4 | 3 | 2 |
| Godless | 0 | 0 | 0 | 4 |

Earlier rounds established that faith parity is about benches rather than head
count, so the roster was built to that shape directly. Keeping all four Godless
in Commons is what makes it possible — Commons seats one courtier, so it is the
only estate with slack to spare. The result: the three faiths land within 1.3
points of each other.

Balance now asks for all three faiths. Letting it settle for any two is worth
about three points to it (34.4% → 37.3%).

### What the Balance threshold buys

`--balance-seats` sets how full the court must be before Balance counts. The
board averages 5.8 filled seats at a win, so anything up to five is a rule that
is usually already true. 6,000 games each, on the three-faith board:

| Threshold | Balance | naive wins Balance | mean turns |
|---|---|---|---|
| 4 of 7 | 45.5% | 28.9% | 49.4 |
| 5 of 7 | 44.2% | 29.2% | 50.0 |
| 6 of 7 | 41.5% | 25.5% | 51.1 |
| **7 of 7 (current)** | **34.3%** | **20.1%** | 53.3 |

The middle column is the one that matters: it is how often a player who is not
trying wins Balance. Only the full seven brings it into line with the rest of
the board — at 20.1% it now sits alongside Barbarian Conquest's 18.8%, where at
five seats it was nearly double anything else.

Win rate per deal by tier, on the current board:

| Agenda | naive | greedy | strategic |
|---|---|---|---|
| Barbarian Conquest | 18.8% | 38.8% | 69.9% |
| Balance | 20.1% | 28.6% | 66.1% |
| House Rising (mean) | 12.9% | 23.5% | 58.9% |
| Faith Ascendant (mean) | 6.9% | 17.6% | 49.7% |

The faiths have become the board's skill agendas: a bot playing at random
almost never lands one, and even the greedy bot only manages 17.6%.

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

**Treasure Fleet is the only helpful event.** Every other event is played on
somebody else's courtier; this one installs your own from the outer circle. A
fleet arriving in harbour reads badly as a disaster, and a card whose target is
a friend adds texture — but if events should be uniformly hostile it is one
line to change. `docs/RULES.md` has the alternative.
