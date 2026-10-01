# Balance: what the bots found

Batch runs of the simulator (`python -m succession run`), and what each rules
change did to the numbers. How to run your own is in
[DEVELOPING.md](DEVELOPING.md).

## First findings

6,000 games, default mix (`naive, greedy, strategic, naive`, seats shuffled):

```
Game length: mean 53.6 player-turns (13.8 rounds), median 47, max 233
Double wins: 6.5%          Timeouts: 0%

Win rate by tier      naive 10.5%   greedy 27.0%   strategic 58.4%

Win rate by agenda    Barbarian Conquest              31.6%
                      House Rising: Amonides          27.1%
                      House Rising: Mitreas           26.4%
                      Balance                         26.0%
                      Faith Ascendant: Mystery Cults  25.7%
                      Faith Ascendant: The One God    25.7%
                      House Rising: Argaian           25.4%
                      Faith Ascendant: Old Gods       25.1%
```

1. **All eight agendas sit inside 6.5 points**, from 25.1% to 31.6%, against
   2–53% under the first draft of the rules. The three faiths finish within 0.6
   points of each other and the three houses within 1.7.

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
   | without a strategic bot | 26.6% | 41.5 turns |
   | with a strategic bot | 16.0% | 53.6 turns |

Games always resolved: no timeouts in 24,000 games at the old 600-turn cap. (The game now ends after 50 rounds with no winner; see [RULES.md](RULES.md).)

### Discard & Draw

Those numbers predate Discard & Draw, which replaces a discarded card at once.
It changes less than it sounds: about a quarter of all turns are discards, but
hands mostly sit at the limit of seven, where the top-of-turn draw was skipped
anyway, so the replacement mostly arrives a turn sooner rather than adding a
card. Over 4,000 games each (`--seed 1`, default mix):

| | plain discard | Discard & Draw |
|---|---|---|
| strategic / greedy / naive | 58.3% / 27.6% / 10.4% | 59.9% / 26.0% / 10.0% |
| spread across the eight agendas | 7.0 points | 4.6 points |
| Barbarian Conquest (the top agenda) | 31.5% | 29.3% |
| mean game length | 54.3 turns | 54.3 turns |
| double wins | 6.6% | 5.9% |

The bots price a discard the way they always have: their lookahead does not
draw the replacement, which would show them the top of the deck.

### One cynic makes the faiths divide evenly

Forty courtiers do not divide by three. Exactly one is born Godless — the Dog
of the Agora, a barefoot street philosopher who sleeps in a wine jar — and
taking him off the top leaves thirty-nine, so the three faiths get thirteen
each with an identical bench in every estate:

| | Church | Military | Merchant | Commons |
|---|---|---|---|---|
| Old Gods | 3 | 4 | 3 | 3 |
| Mystery Cults | 3 | 4 | 3 | 3 |
| The One God | 3 | 4 | 3 | 3 |
| The Dog of the Agora | — | — | — | 1 |

It is worth doing. At 14 / 13 / 13 the faith holding the odd card led the other
two by about a point and a half, and the lead moved when the card did. At
13 / 13 / 13 they finish within 1.2 points. Everyone else reaches godlessness
the hard way, through Apostasy.

### What the Balance threshold buys

`--balance-seats` sets how full the court must be before Balance counts. Six is
the default: one empty chair is allowed, a second is not.

Seven was the default for a while, chosen to stop a careless player falling
into Balance by accident. That premise rested on a blind spot — the bots were
badly under-using purges and freezes, so courts filled up more than they should
have. Once the events were priced properly, a full court became rare enough
that Balance dropped to 20.8%, five points clear of anything else at the
bottom, and the spread across the eight agendas blew out to 13 points.

6,000 games each, on the corrected bots:

| Threshold | Balance | naive wins Balance | spread across all eight |
|---|---|---|---|
| **6 of 7 (current)** | **26.0%** | 13.0% | **6.5 points** |
| 7 of 7 | 20.8% | 9.7% | 13.0 points |

The accident problem does not come back at six. The naive bot's overall win
rate is 10.5%, so winning Balance 13.0% of the time is barely above its own
average — nothing like the 25.5% that made the change worth doing in the first
place.

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
