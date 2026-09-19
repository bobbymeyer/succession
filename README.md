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
Game length: mean 39.5 player-turns (10.2 rounds), median 36, max 192
Double wins: 7.4%          Timeouts: 0%

Win rate by tier      naive 14.1%   greedy 24.8%   strategic 54.6%

Win rate by agenda    Faith Ascendant: Mystery Cults  39.6%
                      Faith Ascendant: Old Gods       39.4%
                      Balance                         38.1%
                      Barbarian Conquest              27.6%
                      House Rising: Argaian           14.3%
                      House Rising: Amonides          14.2%
                      House Rising: Mitreas           13.9%
```

1. **The seven agendas span 14–40%**, against 2–53% under the first draft of
   the rules. Three of them sit inside a point of each other at ~39%, and the
   three houses within 0.4 points — which is what you want from copies of one
   agenda.

2. **The third own-estate courtier per house is what closed the gap.** Houses
   went 11% → 14% when each family gained a third courtier in its own estate:
   a house no longer has to spend both of its estate cards to claim the seat
   its agenda demands.

3. **Barbarian Conquest is now the outlier at 27.6%**, and it moved without
   being touched — three more Imperial courtiers dilute the barbarian share of
   the deck (8 of 37, down from 8 of 34), and the new Argaian courtier is
   Military, so it competes directly for the two seats the generals route
   needs. If you want it back near 33%, the lever is a ninth barbarian rather
   than a rule change.

4. **The two faiths are at parity** (39.6% / 39.4%) despite the roster now
   being 19 Old Gods to 18 Mystery Cults — the odd courtier out does not show
   up above the noise.

5. **The tiers separate cleanly**, which is the sanity check that the bots are
   really playing the game: 14.1% → 24.8% → 54.6%. A strategic bot at the table
   also suppresses everyone else. Swapping exactly one greedy seat for a
   strategic seat (4,000 games each, everything else held fixed):

   | | other three players' win rate | mean game length |
   |---|---|---|
   | without a strategic bot | 26.9% | 27.8 turns |
   | with a strategic bot | 17.6% | 39.5 turns |

   It takes about a third of the other players' equity and makes games ~40%
   longer — it is genuinely denying wins, not just winning faster.

Games always resolve: no timeouts in 16,000 games at the 600-turn cap.

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
