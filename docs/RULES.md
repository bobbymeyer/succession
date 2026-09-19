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
| Courtier (37) | Enters the outer circle. |
| Promotion (5) | Outer courtier → an *occupied* matching seat; occupant bumped to outer. Wildcard `Promotion` works on any estate. |
| Demotion (5) | Inner courtier → outer; seat left empty. |
| Removal (6) | Courtier leaves play. `Targeted Poisoning` allows a d6 save (even = saved); the rest do not. |
| Defense (5) | Attached preemptively to an inner-circle courtier by sacrificing a matching-estate courtier *from hand* (`Patron Protection`: any estate). Negates the first Removal / Demotion / Strip / Mutation aimed at that courtier, then is discarded. **Does not stop Events.** |
| Strip (2) | `Castration` sets Family → None, `Excommunication` sets Faith → None. The courtier stays where they are. |
| Mutation (8) | Changes one attribute. Each attribute may be mutated **at most once per courtier**. An estate mutation that un-matches an inner seat demotes its holder immediately. |
| Event (10) | The player playing it names **one target courtier**. Minor: the target may attempt a save. Major: no save. |
| Outmaneuver (1) | The targeted player skips their next turn. |
| Pivot (1) | `Schismatic Event`: discard your agenda, draw a new one from the unused pool. The act is public; both agendas stay private. |

Strips do **not** consume a courtier's mutation allowance, so a stripped
attribute can be restored later by `Conversion` (the player picks the faith) or
`Adoption`.

A card with no legal target cannot be played at all that turn — the engine
never generates an action that would do nothing.

## Winning

Checked after every action resolves, on any player's turn. A player whose
agenda the board satisfies wins. If two agendas are satisfied by the same board
state, **both** players win and the game is logged as a double win.

| Agenda | Copies | Condition |
|---|---|---|
| House Rising | 3 (one per family) | That family holds **3+** of the 7 inner seats, **at least one of them in the family's own estate** |
| Faith Ascendant | 2 (one per faith) | That faith holds 4+ of the 7 inner seats (`--faith-seats` to change) |
| Barbarian Conquest | 1 | **3 barbarians in the inner circle**, *or* both Military seats held by barbarians |
| Balance | 1 | Inner circle simultaneously shows all three families, both faiths, and a barbarian |

Barbarian Conquest has two routes and either one wins outright: a bloc of
three seated barbarians anywhere in the inner circle, or both generals. Two
barbarian generals therefore win on their own.

Each house's own estate comes from the source document's affiliations and
lives in `FAMILY_PREFERRED_ESTATE` in `succession/courtiers.py`:

| House | Own estate | Seats available |
|---|---|---|
| Amonides | Church | Chief Priest, Oracle |
| Mitreas | Merchant | Master of the Exchequer, Harbormaster |
| Argaian | Military | Field General, Praetorian Chief |

Every family fields **three** courtiers in its own estate and two in each of
the other two, and every estate that a house can be affiliated with seats a
pair, so no house is short of candidates for its own estate. Three seats that avoid the family's estate entirely -- two
Military plus the Exchequer for Amonides, say -- is not a win.
`--house-preferred-estates mitreas=church` overrides one family's estate;
`--house-any-three` drops the requirement altogether.

Four of the seven agendas are dealt out; the other three stay in fog and are
the pool `Schismatic Event` draws from.

## Deck

80 cards: 37 courtiers + 10 events + 5 promotions + 5 demotions + 6 removals +
5 defenses + 2 strips + 8 mutations + 1 pivot + 1 Outmaneuver. When the draw
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
