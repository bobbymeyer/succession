# Rules as implemented

This is the engine's contract. Everything the handoff brief stated is
implemented literally; everything it left open is listed under **Assumptions**
with the config flag that flips it, and under **Open questions for Bobby**
where a real design decision is still owed.

## Board

Seven inner seats, each locked to one estate. Only a courtier whose *current*
estate matches may occupy a seat.

| Seat | Estate |
|---|---|
| Archpriest | Church |
| Oracle | Church |
| Lord General | Military |
| Captain of the Guard | Military |
| Keeper of the Treasury | Merchant |
| Master of the Market | Merchant |
| Voice of the People | Commons |

Church, Military and Merchant each seat a mechanically identical pair; Commons
seats one. The engine treats the members of a pair as interchangeable when a
card only needs "an empty matching seat". The names are archetypes rather than
settled flavour: they live in `Seat` in `succession/enums.py` and nothing else
depends on the spelling, so renaming one is a one-line change.

The **outer circle is a single shared court**, not a per-player tableau.
Nobody owns a courtier: agendas are read off the board, and any player may
move any outer courtier into an empty matching seat.

## Turn

**Draw one card, then take exactly one action.** The card drawn at the top of
the turn can be played that same turn. A hand already at the limit of 7 draws
nothing. Turn order is clockwise; the first player is chosen at random.

1. **Play a card from hand** — a card from hand only ever reaches the outer
   circle. There is no way to play a card from hand straight into a seat.
2. **Move** — free, no card: take an outer courtier and install them in an
   *empty* seat of their estate.
3. **Discard & Draw** — discard a card and draw a replacement at once. If the
   deck is empty the discard pile, the card just thrown included, is shuffled
   in first. (`--discard-no-draw` restores the plain discard.)

An **occupied** seat can only be taken with a promotion card; the sitting
courtier is bumped to the outer circle.

## Card resolution

| Kind | Effect |
|---|---|
| Courtier (40) | Enters the outer circle. |
| Promotion (5) | Outer courtier → an *occupied* matching seat; occupant bumped to outer. Wildcard `Promotion` works on any estate. |
| Demotion (5) | Inner courtier → outer; seat left empty. |
| Removal (6) | Courtier leaves play. `Targeted Poisoning` allows a d6 save (even = saved); the rest do not. |
| Defense (5) | Attached preemptively to an inner-circle courtier by sacrificing a matching-estate courtier *from hand* (`Patron Protection`: any estate). Negates the first Removal / Demotion / Strip / Mutation aimed at that courtier, then is discarded. **Does not stop Events.** |
| Strip (2) | `Castration` sets Family → None, `Excommunication` sets Faith → None. The courtier stays where they are. |
| Mutation (9) | Changes one attribute. Each attribute may be mutated **at most once per courtier**. An estate mutation that un-matches an inner seat demotes its holder immediately. |
| Event (10) | Hits the whole table, not one courtier. Five minor/major pairs -- see below. No Defense covers an event. |
| Outmaneuver (1) | The targeted player skips their next turn. |
| Pivot (1) | `Schismatic Event`: discard your agenda, draw a new one from the unused pool. The act is public; both agendas stay private. |

Strips do **not** consume a courtier's mutation allowance, so a stripped
attribute can be restored later by `Conversion` (the player picks the faith) or
`Adoption`.

## Faith and godlessness

Three faiths -- **Old Gods**, **Mystery Cults** and **The One God** -- each with
its own Faith Ascendant agenda. Godlessness is a real position rather than an
absence, and **exactly one courtier is born into it**: the Dog of the Agora, a
barefoot cynic who sleeps in a wine jar and carries a lamp through the market
at noon looking for an honest man. Everyone else reaches godlessness the hard
way, through Apostasy.

He earns his place twice over. Forty courtiers do not divide by three; taking
the cynic off the top leaves thirty-nine, so the three faiths come out at
thirteen apiece with an identical bench in every estate:

| | Church | Military | Merchant | Commons |
|---|---|---|---|---|
| Old Gods | 3 | 4 | 3 | 3 |
| Mystery Cults | 3 | 4 | 3 | 3 |
| The One God | 3 | 4 | 3 | 3 |
| The Dog of the Agora | — | — | — | 1 |

Before him the roster ran 14 / 13 / 13 and the faith holding the odd card led
the other two by about a point and a half; the lead moved when the card did.
With him it is 13 / 13 / 13 and the three faiths finish within 1.2 points of
each other.

House Amonides remains wholly Old Gods and House Mitreas wholly Mystery Cults.
The One God is a newer faith: it has spread among the commoners and the
frontier peoples, and House Argaian -- the mixed-faith house -- is the only one
that has taken it up.

Godlessness has no agenda. There is no Faith Ascendant: Godless, and Balance
asks for the three faiths, so **a godless courtier in an inner seat is a seat
no faith can count**. That makes it purely denial: the one attribute you push a
courtier into to take something away rather than to build something.

Two cards move a courtier across that line, and each spends the courtier's one
faith mutation, so nobody crosses it twice:

* **Apostasy** (mutation) -- target's faith becomes Godless.
* **Conversion** (mutation) -- moves a courtier to any faith but their own; a
  godless or excommunicated courtier can be brought to any of the three.

Godless is distinct from the `None` an `Excommunication` leaves: `None` is an
empty slot, godlessness is a conviction. Both count for no faith agenda; only
the distinction in the log tells you which happened.

Because Apostasy advances nobody's agenda, the greedy bot never plays it --
0 of 52 draws over 4,000 games -- while the strategic bot plays 93% of the ones
it draws. It is the first card in the deck that separates those two tiers
outright.

## Winning

Checked after every action resolves, on any player's turn. A player whose
agenda the board satisfies wins. If two agendas are satisfied by the same board
state, **both** players win and the game is logged as a double win.

| Agenda | Copies | Condition |
|---|---|---|
| House Rising | 3 (one per family) | That family holds **3+** of the 7 inner seats, **at least one of them in the family's own estate** |
| Faith Ascendant | 3 (one per faith) | That faith holds 4+ of the 7 inner seats (`--faith-seats` to change) |
| Barbarian Conquest | 1 | **3 barbarians seated in the inner circle** |
| Balance | 1 | **Six of the seven seats filled**, and the inner circle simultaneously shows all three families, all three faiths, and **two** barbarians (`--balance-seats`, `--balance-barbarians`) |

Barbarian Conquest is one clause: three barbarians holding inner seats, in any
estates. There is no shortcut for taking both Military seats -- two barbarian
generals are simply two of the three.

Each house also fields one commoner -- its charioteer -- which is the only way
a house can ever hold the Voice of the People's seat.

Each house's own estate comes from the source document's affiliations and
lives in `FAMILY_PREFERRED_ESTATE` in `succession/courtiers.py`:

| House | Own estate | Seats available |
|---|---|---|
| Amonides | Church | Archpriest, Oracle |
| Mitreas | Merchant | Keeper of the Treasury, Master of the Market |
| Argaian | Military | Lord General, Captain of the Guard |

Every family fields **three** courtiers in its own estate, two in each of the
other two, and one charioteer, and every estate that a house can be affiliated with seats a
pair, so no house is short of candidates for its own estate. Three seats that avoid the family's estate entirely -- two
Military plus the Keeper of the Treasury for Amonides, say -- is not a win.
`--house-preferred-estates mitreas=church` overrides one family's estate;
`--house-any-three` drops the requirement altogether.

Four of the eight agendas are dealt out; the other four stay in fog and are
the pool `Schismatic Event` draws from.

## Deck

84 cards: 40 courtiers + 10 events + 5 promotions + 5 demotions + 6 removals +
5 defenses + 2 strips + 9 mutations + 1 pivot + 1 Outmaneuver. When the draw
pile empties, the discard pile is shuffled into a new deck.

---

# Assumptions

Each of these is a decision the brief did not settle. The default is listed
first; the flag flips it.

| # | Decision | Default | Flag |
|---|---|---|---|
| 1 | **Killed courtiers go to the discard** and may reshuffle back as a *new* person with printed attributes (this is what "a killed courtier can reshuffle back in as a 'new' person, never a resurrection" implies). | return to discard | `--removed-out-of-game` takes them out for good |
| 2 | **Balance wants two barbarians, Conquest three.** Both were tuned down from a board where they led every other agenda by five points. | 2 / 3 | `--balance-barbarians` |
| 2b | **A house's own estate is its affiliation from the source document** (Amonides/Church, Mitreas/Merchant, Argaian/Military). | that table | `--house-preferred-estates` overrides a family; `--house-any-three` drops the requirement |
| 2f | **All eight agendas are in the pool.** `--drop-agendas balance` takes one out entirely -- neither dealt nor reachable by a Schismatic Event. | all eight | `--drop-agendas` |
| 2d | **Balance asks for all three faiths**, but not for a godless courtier, since godlessness has no agenda. | three faiths | -- |
| 2e | **Apostasy is a mutation**, so it spends the target's one faith change and a Defense stops it. | mutation | -- |
| 2g | **Balance needs six of the seven seats filled.** One empty chair is allowed, a second is not. Seven was tried and proved too fragile once the bots used purges and freezes properly -- it fell five points clear of everything else at the bottom. | 6 | `--balance-seats` |
| 2c | **Faith Ascendant stayed at four seats** when the board grew to seven, so it is now a bare majority rather than two-thirds. | 4 of 7 | `--faith-seats 5` |
| 3 | **A Defense may protect any inner-circle courtier**; only the *sacrifice* must match the defense's estate (the brief only constrains the sacrifice). | any target | `--defense-matches-target` |
| 4 | **Starting hand is 5 cards**, one Outmaneuver copy in the deck. | 5 / 1 | `--starting-hand`, `--outmaneuver-copies` |
| 5 | Defense is checked **before** a save roll, so a shielded courtier spends the shield rather than rolling. | — | — |
| 6 | A courtier who leaves play loses any attachment and reverts to printed attributes, so an epithet that reshuffles back arrives on a new person. | — | — |
| 7 | **The false-reveal rule is not exercised.** The brief has it that a premature reveal stays revealed and the game continues without that player's fog. A bot has no reason to bluff, so none does, and nothing reads `GameState.revealed` but the win check. Simulating bluffing would need a deliberate-reveal action and a strategic bot that plays differently against a known agenda. | — | — |
| 8 | A skipped turn (Outmaneuver) consumes the whole turn, so the skipped player never reaches their draw. | — | — |

# Event effects

Events are **not aimed at a courtier**: each one hits the whole table. They come
in five minor/major pairs, the major being the harsher half. Only the purge has
anything to save against, and only its minor half allows the roll. No Defense
covers any event.

| Pair | Minor | Major |
|---|---|---|
| **Freeze** | **Quarantine** — the inner circle is sealed for a round | **Siege** — the whole board is sealed for a round |
| **Purge** | **Poisoning at the Feast** — every player names a courtier to kill; each may save on an even d6 | **Plague** — the same, and nobody is spared |
| **Windfall** | **Caravan** — every player draws a card | **Treasure Fleet** — every player draws two |
| **Want** | **Debasement of the Coinage** — every player discards a card | **Famine** — every player discards two |
| **Upheaval** | **Eclipse** — the discard pile is shuffled back into the deck | **Meteor** — every hand is shuffled in and dealt back out |

## What a freeze stops

A freeze runs **until just before the caster's next turn**, so every other
player takes one turn under it.

* **Quarantine** seals the seats. No promotion, no demotion, no free move into
  an empty seat, and no Defense attached (defenses only go on seated
  courtiers). A seated courtier cannot be removed, stripped or mutated, and a
  purge played during it can only reach the outer circle. Courtiers can still
  be played to the outer circle, and outer courtiers can still be targeted.
* **Siege** seals everything. Nothing enters the board, leaves it or changes on
  it. What still works is what never touches a courtier: discarding,
  Outmaneuver, Schismatic Event, and the four non-purge event pairs — including
  another freeze.

## How a purge runs

Starting with the player who played the card and going clockwise, **every
player names one courtier in play**, and that courtier dies — to the discard,
so the epithet may return on somebody new. Each name is taken in turn against
the board as it then stands, so a courtier already named cannot be named again.
Under Poisoning the target rolls a d6 and survives on an even; under Plague
there is no roll. A purge with nobody left to kill cannot be played.

## Decisions this needed

The brief gave the effects but not these edges:

| Decision | Chosen |
|---|---|
| How long "a round" lasts | Until just before the caster's next turn — every other player gets one turn under it |
| Whether the caster is also hit by their own draw, discard or purge | Yes; "every player" includes them |
| Draw order and hand limit | Clockwise from the caster, and the limit of 7 still applies, so a full hand draws nothing |
| What Meteor deals back | Each player gets back as many cards as they held, with the contents randomised |
| Whether Eclipse shuffles itself in | No — it resolves, then goes to the discard |
| Whether a Defense stops any of it | No, exactly as the brief has it |

## A simulator note: how the bots value events

Lookahead scores boards, and four of the five event pairs touch hands and the
deck instead. Three things make the bots price them sensibly, and none of them
is a rule:

* **`hand_edge`** puts a small card-economy term in the score, so a draw or a
  discard shows up as a change the clone can actually see. This is what makes
  Caravan and Treasure Fleet playable at all: before it, they scored below
  throwing the card away and were never played once in 1,500 games.
* **`event_bonus`** covers only what a one-ply clone cannot see -- a freeze,
  whose value is the turns it denies everyone else; a table-wide discard, which
  is symmetric except in the part only we can see; and the two shuffles.
* **Its own purge pick.** When a bot weighs Poisoning or Plague, it models the
  courtier *it* would name as one it chooses well, and leaves the other
  players' picks to a deterministic stand-in.

Play rates over 1,500 games, as a share of the times a bot held the card:

| Event | naive | greedy | strategic |
|---|---|---|---|
| Quarantine / Siege | ~51% | 31% / 32% | 38% / 34% |
| Poisoning / Plague | ~49% | 0% / 0% | 84% / 87% |
| Caravan / Treasure Fleet | ~52% | 80% / 68% | 84% / 91% |
| Debasement / Famine | ~51% | 31% / 34% | 35% / 32% |
| Eclipse / Meteor | ~50% | 35% / 72% | 32% / 63% |

The greedy bot never plays a purge, and that is the tier behaving as defined
rather than a gap: killing courtiers advances nobody's agenda, so a bot that
only advances its own has no use for it. Apostasy is the same.

`tests/test_rules.py::TestEventValuation` pins the direction of each heuristic
-- a freeze is worth more with a lead, a discard when our own hand is dead, a
reshuffle when the deck is short -- without pinning the numbers.

# Open question: how many seats should a faith need?

Faith Ascendant was "4 of 6" -- two-thirds. The board is now seven seats, so
four is a bare majority and the faiths became the two strongest agendas.
`--faith-seats 5` restores the two-thirds shape (2,500 games each):

| Agenda | 4 of 7 (default) | 5 of 7 |
|---|---|---|
| Faith Ascendant: Mystery Cults | 41.3% | 21.3% |
| Faith Ascendant: Old Gods | 39.5% | 18.4% |
| Balance | 37.6% | 48.3% |
| Barbarian Conquest | 32.9% | 40.8% |
| House Rising (mean) | 11.1% | 16.6% |

Five is not obviously better: it does not tighten the overall spread (14-48%
against 11-41%), it just hands the lead to Balance, and it stretches the mean
game from 42 to 49 player-turns. Four is the current default.
