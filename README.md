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
Game length: mean 48.6 player-turns (12.5 rounds), median 44, max 260
Double wins: 6.2%          Timeouts: 0%

Win rate by tier      naive 12.5%   greedy 24.2%   strategic 57.0%

Win rate by agenda    Balance                         39.9%
                      Faith Ascendant: Old Gods       39.8%
                      Faith Ascendant: Mystery Cults  39.4%
                      Conquest                        23.1%
                      House Rising: Amonides          14.5%
                      House Rising: Mitreas           14.1%
                      House Rising: Argaian           13.4%
```

1. **The agendas are in a playable band now** — 13% to 40%, against 2% to 53%
   under the first draft of the rules. Balance and the two faiths sit together
   at ~40%, which makes sense: they are all "get four-ish of the six seats to
   look a certain way" and they can be built incidentally.

2. **Conquest is now the second-hardest, not the easiest.** Requiring the three
   barbarians *in the inner circle* is a much sharper constraint than it looks:
   of the eight barbarians, only one is Church, one Merchant and two Commons,
   so at most five could ever be seated at once, and the two Military seats are
   the most-contested on the board. It dropped from 53% to 23%. If that reads
   as too harsh, the cheapest dial is to let the two generals count toward the
   three rather than requiring a third barbarian elsewhere.

3. **House Rising at three seats works** — ~14% each, and the three houses are
   within a point of each other, which is what you want from three copies of
   the same agenda. It is still the hardest agenda, because it is the only one
   that needs three *specific* courtiers of a six-card subset seated at the
   same time.

4. **The tiers separate cleanly**, which is the sanity check that the bots are
   really playing the game: 12.5% → 24.2% → 57.0%. A strategic bot at the table
   also suppresses everyone else. Swapping exactly one greedy seat for a
   strategic seat (4,000 games each, everything else held fixed):

   | | other three players' win rate | mean game length |
   |---|---|---|
   | without a strategic bot | 26.7% | 35.2 turns |
   | with a strategic bot | 16.4% | 48.6 turns |

   It takes almost 40% of the other players' equity and makes games ~40%
   longer — it is genuinely denying wins, not just winning faster.

Games always resolve: no timeouts in 16,000 games at the 600-turn cap.

### Variant already wired up

`--house-estate-pair` (a House Rising trio must include two seats of one
estate) over 4,000 games takes the houses from ~14% to ~9% and leaves
everything else roughly where it was. See the open question in `docs/RULES.md`
about which reading you meant.

## What still needs you

`docs/RULES.md` ends with the open questions. Two of them matter.

**House Rising's estate pair.** "Each family preferring 2 seats in one estate"
is implemented as the soft reading (any three seats win) with the strict
reading behind `--house-estate-pair`. Worth knowing before you choose: only
Church and Military have two inner seats, so a *per-family* preferred estate
(Amonides/Church, Mitreas/Merchant, Argaian/Military) cannot be a hard
requirement for Mitreas — there is only one Merchant seat to take.

**Event effects.** The bigger one: the brief called out that the source document's effects were written
for the board-wide version and do not map onto single-target. The ten events
currently use a playable placeholder table (all in one place in `cards.py`),
but three of them duplicate "target leaves play", and `Treasure Fleet` is
implemented as a *helpful* event — both worth a decision before the balance
numbers above mean much.
