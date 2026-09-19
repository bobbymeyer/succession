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
| Chief Priest | Church |
| Oracle | Church |
| Field General | Military |
| Praetorian Chief | Military |
| Master of the Exchequer | Merchant |
| Harbormaster | Merchant |
| Guildmaster | Commons |

Church, Military and Merchant each seat a mechanically identical pair; Commons
seats one. The engine treats the members of a pair as interchangeable when a
card only needs "an empty matching seat". ("Harbormaster" is a placeholder
name -- it lives in `Seat` in `succession/enums.py` and nothing else depends on
the spelling.)

The **outer circle is a single shared court**, not a per-player tableau.
Nobody owns a courtier: agendas are read off the board, and any player may
move any outer courtier into an empty matching seat.

## Turn

Exactly one action, then draw one card (only if the hand is below the limit of
7). Turn order is clockwise; the first player is chosen at random.

1. **Play a card from hand** — a card from hand only ever reaches the outer
   circle. There is no way to play a card from hand straight into a seat.
2. **Move** — free, no card: take an outer courtier and install them in an
   *empty* seat of their estate.
3. **Discard** a card.

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
| Event (10) | The player playing it names **one target courtier**. Minor: the target may attempt a save. Major: no save. |
| Outmaneuver (1) | The targeted player skips their next turn. |
| Pivot (1) | `Schismatic Event`: discard your agenda, draw a new one from the unused pool. The act is public; both agendas stay private. |

Strips do **not** consume a courtier's mutation allowance, so a stripped
attribute can be restored later by `Conversion` (the player picks the faith) or
`Adoption`.

## Faith and the Godless

There are two faiths -- Old Gods and Mystery Cults -- and a **Godless** value
that is a real position, not an absence. Only the two faiths need to be level
with each other; the Godless have no win path, so they can be few. Four of the
40 courtiers are Godless, one per group:

| Courtier | Group | Estate |
|---|---|---|
| Whisperer to the Serpent | Mitreas | Church |
| Charioteer of the Iron Wheel | Argaian | Commons |
| Ten Thousand Verses | Commoner | Commons |
| Master Swordsmith | Barbarian | Commons |

That leaves the roster at 18 Old Gods, 18 Mystery Cults, 4 Godless. Parity
between the two faiths is about *benches*, not head count -- see the README.

Godlessness has no agenda. There is no Faith Ascendant: Godless, and Balance
still asks only for the two faiths, so **a godless courtier in an inner seat is
a seat neither faith can count**. That makes godlessness purely denial: it is
the one attribute you push a courtier into to take something away rather than
to build something.

Two cards move a courtier across that line, and each spends the courtier's one
faith mutation, so nobody crosses it twice:

* **Apostasy** (mutation) -- target's faith becomes Godless.
* **Conversion** (mutation) -- flips Old Gods and Mystery Cults, and brings a
  godless (or an excommunicated) courtier to a faith of the player's choosing.

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
| Faith Ascendant | 2 (one per faith) | That faith holds 4+ of the 7 inner seats (`--faith-seats` to change) |
| Barbarian Conquest | 1 | **3 barbarians in the inner circle**, *or* both Military seats held by barbarians |
| Balance | 1 | **Five of the seven seats filled**, and the inner circle simultaneously shows all three families, both faiths, and a barbarian (`--balance-seats`) |

Barbarian Conquest has two routes and either one wins outright: a bloc of
three seated barbarians anywhere in the inner circle, or both generals. Two
barbarian generals therefore win on their own.

Each house also fields one commoner -- its charioteer -- which is the only way
a house can ever hold the Guildmaster's seat.

Each house's own estate comes from the source document's affiliations and
lives in `FAMILY_PREFERRED_ESTATE` in `succession/courtiers.py`:

| House | Own estate | Seats available |
|---|---|---|
| Amonides | Church | Chief Priest, Oracle |
| Mitreas | Merchant | Master of the Exchequer, Harbormaster |
| Argaian | Military | Field General, Praetorian Chief |

Every family fields **three** courtiers in its own estate, two in each of the
other two, and one charioteer, and every estate that a house can be affiliated with seats a
pair, so no house is short of candidates for its own estate. Three seats that avoid the family's estate entirely -- two
Military plus the Exchequer for Amonides, say -- is not a win.
`--house-preferred-estates mitreas=church` overrides one family's estate;
`--house-any-three` drops the requirement altogether.

Four of the seven agendas are dealt out; the other three stay in fog and are
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
| 2 | **Barbarian Conquest's "both generals" route means barbarian generals.** Merely occupied seats would make it near-automatic. | barbarians | -- |
| 2b | **A house's own estate is its affiliation from the source document** (Amonides/Church, Mitreas/Merchant, Argaian/Military). | that table | `--house-preferred-estates` overrides a family; `--house-any-three` drops the requirement |
| 2f | **All seven agendas are in the pool.** `--drop-agendas balance` takes one out entirely -- neither dealt nor reachable by a Schismatic Event. | all seven | `--drop-agendas` |
| 2d | **Balance asks only for the two faiths**, not for a godless courtier as well, since godlessness has no agenda. | two faiths | -- |
| 2e | **Apostasy is a mutation**, so it spends the target's one faith change and a Defense stops it. | mutation | -- |
| 2g | **Balance needs five of the seven seats filled**, so a thin board cannot satisfy it by accident. | 5 | `--balance-seats` |
| 2c | **Faith Ascendant stayed at four seats** when the board grew to seven, so it is now a bare majority rather than two-thirds. | 4 of 7 | `--faith-seats 5` |
| 3 | **A Defense may protect any inner-circle courtier**; only the *sacrifice* must match the defense's estate (the brief only constrains the sacrifice). | any target | `--defense-matches-target` |
| 4 | **Starting hand is 5 cards**, one Outmaneuver copy in the deck. | 5 / 1 | `--starting-hand`, `--outmaneuver-copies` |
| 5 | Defense is checked **before** a save roll, so a shielded courtier spends the shield rather than rolling. | — | — |
| 6 | A courtier who leaves play (killed or recalled) loses any attachment and reverts to printed attributes. | — | — |
| 7 | Bots never make a false/premature reveal, so that rule is modelled but never exercised. `GameState.revealed` is the hook if you want to simulate bluffing. | — | — |
| 8 | A skipped turn (Outmaneuver) consumes the whole turn, draw included. | — | — |

# Event effects — placeholder, needs Bobby

The brief flags this explicitly: the source document's event effects were
written for a board-wide version and do not map 1:1 onto "choose one target
courtier". The table below is a **playable placeholder** chosen to give each
card a distinct, mechanically meaningful single-target effect. All of it lives
in one place — `EVENT_CARDS` in `succession/cards.py` — and the primitives are
`succession/engine.py::_resolve_event`.

| Card | Tier | Placeholder effect |
|---|---|---|
| Quarantine | minor (save) | Target is demoted to the outer circle |
| Poisoning at the Feast | minor (save) | Target leaves play |
| Caravan | minor (save) | Target is shuffled back into the draw deck |
| Debasement of the Coinage | minor (save) | Destroy the target's attached Defense; if none, demote them |
| Eclipse | minor (save) | Target's Faith → None |
| Siege | major | Target leaves play |
| Plague | major | Target is shuffled back into the draw deck |
| Treasure Fleet | major | Install the target from outer into an empty matching seat, free |
| Famine | major | Demote the target and destroy their attached Defense |
| Meteor | major | Target leaves play |

Open questions behind that table:

1. **What does each event actually do to a single courtier?** Three of the ten
   currently duplicate "leaves play", which is flat. Each wants its own verb.
2. **Can an event target a courtier in a player's hand or in the deck?**
   Currently no: only courtiers in play (inner or outer) can be targeted.
3. **Are events always hostile?** `Treasure Fleet` is implemented as a
   *helpful* event, which gives the deck a card you play on your own courtier.
   If events are meant to be strictly hostile, say so and it changes.
4. **Minor-event save:** the same d6-even roll as `Targeted Poisoning`. Is the
   save the same across all minor events, or per-card?
5. **Does a Defense really never stop an Event?** Implemented exactly as
   written; worth confirming, because it makes majors unanswerable.

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
