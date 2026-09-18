# Rules as implemented

This is the engine's contract. Everything the handoff brief stated is
implemented literally; everything it left open is listed under **Assumptions**
with the config flag that flips it, and under **Open questions for Bobby**
where a real design decision is still owed.

## Board

Six inner seats, each locked to one estate. Only a courtier whose *current*
estate matches may occupy a seat.

| Seat | Estate |
|---|---|
| Chief Priest | Church |
| Oracle | Church |
| Field General | Military |
| Praetorian Chief | Military |
| Master of the Exchequer | Merchant |
| Guildmaster | Commons |

The two Church seats are mechanically identical, as are the two Military
seats; the engine therefore treats them as interchangeable when a card only
needs "an empty matching seat".

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
| Courtier (34) | Enters the outer circle. |
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
| House Rising | 3 (one per family) | That family holds **3+** of the 6 inner seats |
| Faith Ascendant | 2 (one per faith) | That faith holds 4+ of the 6 inner seats |
| Conquest | 1 | **3 barbarians in the inner circle** and both Military seats held |
| Balance | 1 | Inner circle simultaneously shows all three families, both faiths, and a barbarian |

Each family fields exactly two Church, two Military and two Merchant courtiers
and no commoner, so a House Rising trio normally comes from doubling up on one
of the two-seat estates (both Church seats or both Military seats) plus a
third seat elsewhere. Whether that doubling-up is *required* or merely the
natural path is the one open question below; the default treats any three
seats as a win, and `--house-estate-pair` enforces the pair.

Four of the seven agendas are dealt out; the other three stay in fog and are
the pool `Schismatic Event` draws from.

## Deck

77 cards: 34 courtiers + 10 events + 5 promotions + 5 demotions + 6 removals +
5 defenses + 2 strips + 8 mutations + 1 pivot + 1 Outmaneuver. When the draw
pile empties, the discard pile is shuffled into a new deck.

---

# Assumptions

Each of these is a decision the brief did not settle. The default is listed
first; the flag flips it.

| # | Decision | Default | Flag |
|---|---|---|---|
| 1 | **Killed courtiers go to the discard** and may reshuffle back as a *new* person with printed attributes (this is what "a killed courtier can reshuffle back in as a 'new' person, never a resurrection" implies). | return to discard | `--removed-out-of-game` takes them out for good |
| 2 | **Conquest's Military seats need only be occupied**, by anyone -- the three barbarians it needs are counted in the inner circle, so the two generals need not themselves be barbarians. | any occupants | `--strict-conquest` requires barbarian generals |
| 2b | **A House Rising trio may be any three seats**, in any estates. | any three | `--house-estate-pair` requires two seats of one estate |
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

# Open question: House Rising and its estate pair

"House Rising should be 3 seats, with each family preferring 2 seats in one
estate (Church, Military, Merchant)" reads two ways, and the two differ by
about five points of win rate:

* **Soft (default)** -- the parenthetical describes the roster: each family has
  two courtiers in each of those three estates, so doubling up on the Church or
  Military seats is simply the easiest route to three. Any three seats win.
  House win rate: ~14%.
* **Strict (`--house-estate-pair`)** -- the trio must *contain* two seats of a
  single estate, so one Church + one Military + the Exchequer does not win.
  House win rate: ~9%.

Note that only Church and Military have two inner seats; Merchant and Commons
have one each. So a "preferred estate" per family (Amonides/Church,
Mitreas/Merchant, Argaian/Military) cannot be a hard requirement for Mitreas --
there is only one Merchant seat to take. If you meant a per-family preferred
estate rather than "any doubled-up estate", that needs either a second Merchant
seat or a different rule for Mitreas.
