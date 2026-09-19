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
Game length: mean 41.9 player-turns (10.9 rounds), median 38, max 222
Double wins: 6.1%          Timeouts: 0%

Win rate by tier      naive 14.7%   greedy 24.3%   strategic 52.3%

Win rate by agenda    Faith Ascendant: Mystery Cults  41.3%
                      Faith Ascendant: Old Gods       39.5%
                      Balance                         37.6%
                      Barbarian Conquest              32.9%
                      House Rising: Amonides          11.3%
                      House Rising: Mitreas           11.0%
                      House Rising: Argaian           10.9%
```

1. **The seven agendas span 11–41%**, against 2–53% under the first draft of
   the rules. The top four sit inside 33–41%, and the three houses are within
   0.5 points of each other — which is what you want from three copies of one
   agenda.

2. **The houses at ~11% are still the hardest thing on the board**, and that
   looks like the right shape rather than a problem: House Rising is the only
   agenda needing three *specific* courtiers of a six-card subset seated at
   once. Dropping the own-estate requirement entirely (`--house-any-three`)
   only moves them to ~13%, so the constraint is costing about two points —
   the scarcity of the right courtiers is doing most of the work.

3. **Barbarian Conquest's two routes make it a real agenda** — 32.9%. The
   generals route (two barbarian generals) is the fast one; the three-seat
   bloc is the fallback when the Military seats are contested.

4. **Faith Ascendant is the strongest pair**, because "4 seats" was two-thirds
   of a six-seat board and is a bare majority of seven. `--faith-seats 5`
   restores the two-thirds shape — see `docs/RULES.md` for what that does to
   everything else (short version: it hands the lead to Balance rather than
   tightening the spread).

5. **The tiers separate cleanly**, which is the sanity check that the bots are
   really playing the game: 14.7% → 24.3% → 52.3%. A strategic bot at the table
   also suppresses everyone else. Swapping exactly one greedy seat for a
   strategic seat (4,000 games each, everything else held fixed):

   | | other three players' win rate | mean game length |
   |---|---|---|
   | without a strategic bot | 26.6% | 29.0 turns |
   | with a strategic bot | 17.9% | 41.9 turns |

   It takes about a third of the other players' equity and makes games ~45%
   longer — it is genuinely denying wins, not just winning faster.

Games always resolve: no timeouts in 16,000 games at the 600-turn cap.

### Variants already wired up

| Flag | Effect on the batch |
|---|---|
| `--faith-seats 5` | faiths 18–21%, Balance 48%, Conquest 41%, houses ~17% |
| `--house-any-three` | drops the own-estate requirement; houses ~13% |
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
