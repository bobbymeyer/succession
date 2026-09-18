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
Game length: mean 52.8 player-turns (13.6 rounds), median 47, max 439
Double wins: 4.5%          Timeouts: 0%

Win rate by tier      naive 13.3%   greedy 24.4%   strategic 53.6%

Win rate by agenda    Balance                         43.1%
                      Faith Ascendant: Mystery Cults  42.5%
                      Faith Ascendant: Old Gods       42.1%
                      Conquest                        25.8%
                      House Rising: Amonides           9.4%
                      House Rising: Mitreas            9.0%
                      House Rising: Argaian            8.7%
```

1. **The agendas sit in a playable band** — 9% to 43%, against 2% to 53% under
   the first draft of the rules. Balance and the two faiths cluster at ~42%:
   they are all "get four-ish of the six seats to look a certain way" and they
   can be assembled incidentally. Conquest and the houses are the ones you have
   to actually play for.

2. **The three houses are within 0.7 points of each other**, which is what you
   want from three copies of one agenda. At ~9% they are the hardest thing on
   the board — the estate pair is a real constraint, because only Church and
   Military have two seats, so every house is fighting for the same four seats.

3. **Conquest is the second-hardest at 25.8%.** Requiring the three barbarians
   *in the inner circle* is sharper than it looks: of the eight barbarians only
   one is Church, one Merchant and two Commons, so at most five could ever be
   seated, and the two Military seats are the most-contested on the board. If
   that reads as too harsh, the cheapest dial is letting the two generals count
   toward the three rather than needing a third barbarian elsewhere.

4. **The tiers separate cleanly**, which is the sanity check that the bots are
   really playing the game: 13.3% → 24.4% → 53.6%. A strategic bot at the table
   also suppresses everyone else. Swapping exactly one greedy seat for a
   strategic seat (4,000 games each, everything else held fixed):

   | | other three players' win rate | mean game length |
   |---|---|---|
   | without a strategic bot | 26.5% | 37.6 turns |
   | with a strategic bot | 17.0% | 52.8 turns |

   It takes over a third of the other players' equity and makes games ~40%
   longer — it is genuinely denying wins, not just winning faster.

Games always resolve: no timeouts in 16,000 games at the 600-turn cap.

### Variants already wired up

| Flag | Effect on the batch |
|---|---|
| `--house-preferred-estates amonides=church,mitreas=merchant,argaian=military` | Amonides 5.6%, Argaian 5.6%, **Mitreas 0.0%** — see below |
| `--house-any-three` | drops the pair requirement; houses rise to ~14% |
| `--strict-conquest` | Conquest's two generals must themselves be barbarians |
| `--removed-out-of-game` | killed courtiers never return |
| `--defense-matches-target` | an estate Defense may only shield its own estate |

## What still needs you

`docs/RULES.md` ends with the open questions. Two of them matter.

**Which estate does each family prefer?** Three seats with two in one estate
is implemented. What is still open is whether the preferred estate is *fixed*
per family or simply whichever one they double up in (the default).

The board resists a fixed mapping: only Church and Military have two inner
seats. Running the source document's affiliations for 2,000 games —
`amonides=church,mitreas=merchant,argaian=military` — House Rising: Mitreas
won **0 of 1,086** games, because it can hold every seat it is able to hold
(five of six, having no commoner for the Guildmaster) and still never pair in
Merchant. Amonides and Argaian drop to 5.6% each.

So a fixed mapping needs one of: give Mitreas a two-seat estate, add a second
Merchant seat, or leave the preference emergent. `docs/RULES.md` lays out all
three.

**Event effects.** The bigger one. The brief called out that the source
document's effects were written for the board-wide version and do not map onto
single-target. The ten events currently use a playable placeholder table (all
in one place in `cards.py`), but three of them duplicate "target leaves play",
and `Treasure Fleet` is implemented as a *helpful* event — both worth a
decision before the balance numbers above mean much.
