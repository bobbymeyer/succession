# Court of Succession — playtest alpha

A dependency-free Python simulator for the card-driven succession game: full
card and board model, a rules engine, three tiers of bot, and a CLI that runs
N games and logs each one to CSV or SQLite for balance analysis.

**Playtest alpha.** The rules are settled enough to put in front of players:
every agenda is winnable, the eight of them sit inside seven points of each
other, and 24,000 simulated games resolve without a single stall. What is
alpha about it is that none of it has been played by a human yet — the numbers
come from bots, and the open questions in `docs/RULES.md` are the ones a table
will answer faster than a batch run.

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
Game length: mean 52.5 player-turns (13.5 rounds), median 47, max 264
Double wins: 6.8%          Timeouts: 0%

Win rate by tier      naive 10.6%   greedy 26.8%   strategic 58.9%

Win rate by agenda    Barbarian Conquest              30.5%
                      House Rising: Mitreas           28.0%
                      Faith Ascendant: Old Gods       27.9%
                      House Rising: Amonides          27.1%
                      Faith Ascendant: Mystery Cults  26.1%
                      Faith Ascendant: The One God    25.0%
                      Balance                         24.9%
                      House Rising: Argaian           24.5%
```

1. **All eight agendas sit inside 6.0 points**, from 24.5% to 30.5%, against
   2–53% under the first draft of the rules.

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
   | without a strategic bot | 26.8% | 39.3 turns |
   | with a strategic bot | 16.0% | 52.5 turns |

Games always resolve: no timeouts in 24,000 games at the 600-turn cap.

### Every faith gets the same bench where it counts

Nobody is born Godless — it is somewhere Apostasy sends a courtier, never
somewhere they start. Forty courtiers do not divide by three, so the roster is
14 / 13 / 13, and the odd card is parked in Commons:

| | Church | Military | Merchant | Commons |
|---|---|---|---|---|
| Old Gods | 3 | 4 | 3 | 4 |
| Mystery Cults | 3 | 4 | 3 | 3 |
| The One God | 3 | 4 | 3 | 3 |

Commons seats one courtier against two apiece for the other three estates, so
that is the cheapest place to put an imbalance — but it is not free. Moving the
fourteenth card from Old Gods to Mystery Cults moves the lead with it, worth
about a point and a half. Two more courtiers, one commoner and one barbarian,
would make it 14 / 14 / 14 without touching the houses.

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

**How the bots value events.** Four of the five event pairs touch hands and the
deck rather than the board, and the bots score boards, so they need a heuristic
to rate a Caravan above discarding it. `ThinkingBot.event_bonus` supplies one —
crude on purpose, and the first thing to revisit if the event numbers look
wrong. `docs/RULES.md` lists the other edges the brief left open, such as how
long a freeze runs and what Meteor deals back.
