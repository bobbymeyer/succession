# The deck

All 99 cards, in the order `succession/cards.py` builds them: the 84-card play deck followed by the eight agendas. Every card here is the real print file, trimmed the way the cutter leaves it.

**[Download the print-ready deck](https://github.com/bobbymeyer/succession/releases/latest/download/succession-print-deck.zip)** -- the card images plus the MPC Autofill order file, ready to order. [docs/PRINTING.md](PRINTING.md) has the steps.

Rebuild any of this with `python tools/mpcfill.py` -- see [docs/PRINTING.md](PRINTING.md).

## Contents

- [Courtier](#courtier) (40)
- [Event](#event) (10)
- [Promotion](#promotion) (5)
- [Demotion](#demotion) (5)
- [Removal](#removal) (6)
- [Defense](#defense) (5)
- [Strip](#strip) (2)
- [Mutation](#mutation) (9)
- [Pivot](#pivot) (1)
- [Outmaneuver](#outmaneuver) (1)
- [Agenda](#agenda) (8)
- [Seat](#seat) (7)
- [Card back](#card-back) (1)

## Courtier

Forty courtiers. These four printed attributes are the whole of what an agenda reads off the board. A courtier who dies goes to the discard and may come back as a new person carrying exactly these values again -- never the mutations the dead one had collected.

| | Card | Type | Printed attributes |
|---|---|---|---|
| <img src="cards/01-beloved-of-the-gods.jpg" alt="Beloved of the Gods" width="132"> | **Beloved of the Gods**<br><sub>Card 01</sub> | Courtier · Church | Church · Old Gods · Amonides · Imperial |
| <img src="cards/02-keeper-of-the-long-peace.jpg" alt="Keeper of the Long Peace" width="132"> | **Keeper of the Long Peace**<br><sub>Card 02</sub> | Courtier · Military | Military · Old Gods · Amonides · Imperial |
| <img src="cards/03-hand-of-the-oracle.jpg" alt="Hand of the Oracle" width="132"> | **Hand of the Oracle**<br><sub>Card 03</sub> | Courtier · Church | Church · Old Gods · Amonides · Imperial |
| <img src="cards/04-weigher-of-grain.jpg" alt="Weigher of Grain" width="132"> | **Weigher of Grain**<br><sub>Card 04</sub> | Courtier · Merchant | Merchant · Old Gods · Amonides · Imperial |
| <img src="cards/05-speaker-of-the-old-words.jpg" alt="Speaker of the Old Words" width="132"> | **Speaker of the Old Words**<br><sub>Card 05</sub> | Courtier · Military | Military · Old Gods · Amonides · Imperial |
| <img src="cards/06-wearer-of-the-golden-diadem.jpg" alt="Wearer of the Golden Diadem" width="132"> | **Wearer of the Golden Diadem**<br><sub>Card 06</sub> | Courtier · Merchant | Merchant · Old Gods · Amonides · Imperial |
| <img src="cards/07-tender-of-the-ancestral-flame.jpg" alt="Tender of the Ancestral Flame" width="132"> | **Tender of the Ancestral Flame**<br><sub>Card 07</sub> | Courtier · Church | Church · Old Gods · Amonides · Imperial |
| <img src="cards/08-charioteer-of-the-sun-team.jpg" alt="Charioteer of the Sun Team" width="132"> | **Charioteer of the Sun Team**<br><sub>Card 08</sub> | Courtier · Commons | Commons · Old Gods · Amonides · Imperial |
| <img src="cards/09-golden-thumb.jpg" alt="Golden Thumb" width="132"> | **Golden Thumb**<br><sub>Card 09</sub> | Courtier · Merchant | Merchant · Mystery Cults · Mitreas · Imperial |
| <img src="cards/10-initiate-of-the-seven-veils.jpg" alt="Initiate of the Seven Veils" width="132"> | **Initiate of the Seven Veils**<br><sub>Card 10</sub> | Courtier · Church | Church · Mystery Cults · Mitreas · Imperial |
| <img src="cards/11-crosser-of-rivers.jpg" alt="Crosser of Rivers" width="132"> | **Crosser of Rivers**<br><sub>Card 11</sub> | Courtier · Military | Military · Mystery Cults · Mitreas · Imperial |
| <img src="cards/12-buyer-of-cities.jpg" alt="Buyer of Cities" width="132"> | **Buyer of Cities**<br><sub>Card 12</sub> | Courtier · Merchant | Merchant · Mystery Cults · Mitreas · Imperial |
| <img src="cards/13-whisperer-to-the-serpent.jpg" alt="Whisperer to the Serpent" width="132"> | **Whisperer to the Serpent**<br><sub>Card 13</sub> | Courtier · Church | Church · Mystery Cults · Mitreas · Imperial |
| <img src="cards/14-rider-of-the-long-road.jpg" alt="Rider of the Long Road" width="132"> | **Rider of the Long Road**<br><sub>Card 14</sub> | Courtier · Military | Military · Mystery Cults · Mitreas · Imperial |
| <img src="cards/15-creditor-of-kings.jpg" alt="Creditor of Kings" width="132"> | **Creditor of Kings**<br><sub>Card 15</sub> | Courtier · Merchant | Merchant · Mystery Cults · Mitreas · Imperial |
| <img src="cards/16-charioteer-of-the-seven-turns.jpg" alt="Charioteer of the Seven Turns" width="132"> | **Charioteer of the Seven Turns**<br><sub>Card 16</sub> | Courtier · Commons | Commons · Mystery Cults · Mitreas · Imperial |
| <img src="cards/17-horse-breaker.jpg" alt="Horse Breaker" width="132"> | **Horse Breaker**<br><sub>Card 17</sub> | Courtier · Military | Military · Mystery Cults · Argaian · Imperial |
| <img src="cards/18-destroyer-of-walls.jpg" alt="Destroyer of Walls" width="132"> | **Destroyer of Walls**<br><sub>Card 18</sub> | Courtier · Military | Military · Old Gods · Argaian · Imperial |
| <img src="cards/19-reader-of-omens.jpg" alt="Reader of Omens" width="132"> | **Reader of Omens**<br><sub>Card 19</sub> | Courtier · Church | Church · The One God · Argaian · Imperial |
| <img src="cards/20-sword-of-the-assembly.jpg" alt="Sword of the Assembly" width="132"> | **Sword of the Assembly**<br><sub>Card 20</sub> | Courtier · Church | Church · The One God · Argaian · Imperial |
| <img src="cards/21-founder-of-markets.jpg" alt="Founder of Markets" width="132"> | **Founder of Markets**<br><sub>Card 21</sub> | Courtier · Merchant | Merchant · The One God · Argaian · Imperial |
| <img src="cards/22-uncrowned-victor.jpg" alt="Uncrowned Victor" width="132"> | **Uncrowned Victor**<br><sub>Card 22</sub> | Courtier · Merchant | Merchant · Old Gods · Argaian · Imperial |
| <img src="cards/23-taker-of-the-citadel.jpg" alt="Taker of the Citadel" width="132"> | **Taker of the Citadel**<br><sub>Card 23</sub> | Courtier · Military | Military · The One God · Argaian · Imperial |
| <img src="cards/24-charioteer-of-the-iron-wheel.jpg" alt="Charioteer of the Iron Wheel" width="132"> | **Charioteer of the Iron Wheel**<br><sub>Card 24</sub> | Courtier · Commons | Commons · The One God · Argaian · Imperial |
| <img src="cards/25-silver-tongue.jpg" alt="Silver Tongue" width="132"> | **Silver Tongue**<br><sub>Card 25</sub> | Courtier · Commons | Commons · The One God · None · Imperial |
| <img src="cards/26-the-dog-of-the-agora.jpg" alt="The Dog of the Agora" width="132"> | **The Dog of the Agora**<br><sub>Card 26</sub> | Courtier · Commons | Commons · Godless · None · Imperial |
| <img src="cards/27-mender-of-bones.jpg" alt="Mender of Bones" width="132"> | **Mender of Bones**<br><sub>Card 27</sub> | Courtier · Commons | Commons · Mystery Cults · None · Imperial |
| <img src="cards/28-ten-thousand-verses.jpg" alt="Ten Thousand Verses" width="132"> | **Ten Thousand Verses**<br><sub>Card 28</sub> | Courtier · Commons | Commons · Old Gods · None · Imperial |
| <img src="cards/29-builder-of-the-long-aqueduct.jpg" alt="Builder of the Long Aqueduct" width="132"> | **Builder of the Long Aqueduct**<br><sub>Card 29</sub> | Courtier · Commons | Commons · The One God · None · Imperial |
| <img src="cards/30-risen-from-the-ranks.jpg" alt="Risen from the Ranks" width="132"> | **Risen from the Ranks**<br><sub>Card 30</sub> | Courtier · Military | Military · The One God · None · Imperial |
| <img src="cards/31-coin-counter-of-the-assembly.jpg" alt="Coin-Counter of the Assembly" width="132"> | **Coin-Counter of the Assembly**<br><sub>Card 31</sub> | Courtier · Merchant | Merchant · The One God · None · Imperial |
| <img src="cards/32-widow-of-the-temple.jpg" alt="Widow of the Temple" width="132"> | **Widow of the Temple**<br><sub>Card 32</sub> | Courtier · Church | Church · The One God · None · Imperial |
| <img src="cards/33-priest-of-the-two-horned-god.jpg" alt="Priest of the Two-Horned God" width="132"> | **Priest of the Two-Horned God**<br><sub>Card 33</sub> | Courtier · Church | Church · Mystery Cults · None · Barbarian |
| <img src="cards/34-master-mason.jpg" alt="Master Mason" width="132"> | **Master Mason**<br><sub>Card 34</sub> | Courtier · Commons | Commons · Mystery Cults · None · Barbarian |
| <img src="cards/35-cataphract-of-the-iron-bridge.jpg" alt="Cataphract of the Iron Bridge" width="132"> | **Cataphract of the Iron Bridge**<br><sub>Card 35</sub> | Courtier · Military | Military · The One God · None · Barbarian |
| <img src="cards/36-caravan-lord-of-the-salt-road.jpg" alt="Caravan-Lord of the Salt Road" width="132"> | **Caravan-Lord of the Salt Road**<br><sub>Card 36</sub> | Courtier · Merchant | Merchant · The One God · None · Barbarian |
| <img src="cards/37-hundred-kill-rider.jpg" alt="Hundred-Kill Rider" width="132"> | **Hundred-Kill Rider**<br><sub>Card 37</sub> | Courtier · Military | Military · The One God · None · Barbarian |
| <img src="cards/38-blade-for-any-banner.jpg" alt="Blade for Any Banner" width="132"> | **Blade for Any Banner**<br><sub>Card 38</sub> | Courtier · Military | Military · Mystery Cults · None · Barbarian |
| <img src="cards/39-warlord-of-the-iron-grove.jpg" alt="Warlord of the Iron Grove" width="132"> | **Warlord of the Iron Grove**<br><sub>Card 39</sub> | Courtier · Military | Military · Old Gods · None · Barbarian |
| <img src="cards/40-master-swordsmith.jpg" alt="Master Swordsmith" width="132"> | **Master Swordsmith**<br><sub>Card 40</sub> | Courtier · Commons | Commons · Old Gods · None · Barbarian |

## Event

Ten events in five minor/major pairs. An event hits the whole table rather than one courtier, and no Defense covers one.

| | Card | Type | What it does |
|---|---|---|---|
| <img src="cards/41-quarantine.jpg" alt="Quarantine" width="132"> | **Quarantine**<br><sub>Card 41</sub> | Event · Minor | The seats are sealed until just before your next turn. No promotion, no demotion, no move into an empty seat, and no Defense attached. A seated courtier cannot be removed, stripped or mutated. The outer circle plays on. |
| <img src="cards/42-siege.jpg" alt="Siege" width="132"> | **Siege**<br><sub>Card 42</sub> | Event · Major | The board is sealed until just before your next turn. Nothing enters it, leaves it or changes on it. Discarding, Outmaneuver, Schismatic Event and the non-purge events still work. |
| <img src="cards/43-poisoning-at-the-feast.jpg" alt="Poisoning at the Feast" width="132"> | **Poisoning at the Feast**<br><sub>Card 43</sub> | Event · Minor | Starting with you and going clockwise, every player names one courtier in play, and that courtier dies. Each names against the board as it then stands. A named courtier rolls a d6 and survives on an even. |
| <img src="cards/44-plague.jpg" alt="Plague" width="132"> | **Plague**<br><sub>Card 44</sub> | Event · Major | Starting with you and going clockwise, every player names one courtier in play, and that courtier dies. Each names against the board as it then stands. Nobody is spared. |
| <img src="cards/45-caravan.jpg" alt="Caravan" width="132"> | **Caravan**<br><sub>Card 45</sub> | Event · Minor | Every player draws a card, starting with you and going clockwise. A hand already holding seven draws nothing. |
| <img src="cards/46-treasure-fleet.jpg" alt="Treasure Fleet" width="132"> | **Treasure Fleet**<br><sub>Card 46</sub> | Event · Major | Every player draws two cards, starting with you and going clockwise. A hand already holding seven draws nothing. |
| <img src="cards/47-debasement-of-the-coinage.jpg" alt="Debasement of the Coinage" width="132"> | **Debasement of the Coinage**<br><sub>Card 47</sub> | Event · Minor | Every player discards a card, starting with you and going clockwise. |
| <img src="cards/48-famine.jpg" alt="Famine" width="132"> | **Famine**<br><sub>Card 48</sub> | Event · Major | Every player discards two cards, starting with you and going clockwise. |
| <img src="cards/49-eclipse.jpg" alt="Eclipse" width="132"> | **Eclipse**<br><sub>Card 49</sub> | Event · Minor | Shuffle the discard pile back into the deck. This card resolves first and then goes to the new discard. |
| <img src="cards/50-meteor.jpg" alt="Meteor" width="132"> | **Meteor**<br><sub>Card 50</sub> | Event · Major | Every hand is shuffled into the deck and dealt back out. Each player receives as many cards as they were holding. |

## Promotion

Takes an *occupied* seat of the named estate, bumping the sitting courtier out to the outer circle. The wildcard `Promotion` works on any estate.

| | Card | Type | What it does |
|---|---|---|---|
| <img src="cards/51-promotion.jpg" alt="Promotion" width="132"> | **Promotion**<br><sub>Card 51</sub> | Promotion · Any Estate | Move an outer-circle courtier into an occupied seat of their estate. The sitting courtier is bumped to the outer circle. |
| <img src="cards/52-battlefield-promotion.jpg" alt="Battlefield Promotion" width="132"> | **Battlefield Promotion**<br><sub>Card 52</sub> | Promotion · Military | Move an outer-circle Military courtier into an occupied Military seat. The sitting courtier is bumped to the outer circle. |
| <img src="cards/53-consecration.jpg" alt="Consecration" width="132"> | **Consecration**<br><sub>Card 53</sub> | Promotion · Church | Move an outer-circle Church courtier into an occupied Church seat. The sitting courtier is bumped to the outer circle. |
| <img src="cards/54-royal-charter.jpg" alt="Royal Charter" width="132"> | **Royal Charter**<br><sub>Card 54</sub> | Promotion · Merchant | Move an outer-circle Merchant courtier into an occupied Merchant seat. The sitting courtier is bumped to the outer circle. |
| <img src="cards/55-acclamation.jpg" alt="Acclamation" width="132"> | **Acclamation**<br><sub>Card 55</sub> | Promotion · Commons | Move an outer-circle Commons courtier into the Voice of the People's seat. The sitting courtier is bumped to the outer circle. |

## Demotion

Sends an inner-circle courtier out and leaves the seat empty.

| | Card | Type | What it does |
|---|---|---|---|
| <img src="cards/56-demotion.jpg" alt="Demotion" width="132"> | **Demotion**<br><sub>Card 56</sub> | Demotion · Any Estate | Send an inner-circle courtier to the outer circle. Their seat is left empty. |
| <img src="cards/57-heresy-accusation.jpg" alt="Heresy Accusation" width="132"> | **Heresy Accusation**<br><sub>Card 57</sub> | Demotion · Church | Send an inner-circle Church courtier to the outer circle. Their seat is left empty. |
| <img src="cards/58-cashiering.jpg" alt="Cashiering" width="132"> | **Cashiering**<br><sub>Card 58</sub> | Demotion · Military | Send an inner-circle Military courtier to the outer circle. Their seat is left empty. |
| <img src="cards/59-charter-revoked.jpg" alt="Charter Revoked" width="132"> | **Charter Revoked**<br><sub>Card 59</sub> | Demotion · Merchant | Send an inner-circle Merchant courtier to the outer circle. Their seat is left empty. |
| <img src="cards/60-ostracism.jpg" alt="Ostracism" width="132"> | **Ostracism**<br><sub>Card 60</sub> | Demotion · Commons | Send the Voice of the People to the outer circle. The seat is left empty. |

## Removal

Takes a courtier out of play. They go to the discard, so the epithet may return later on somebody new.

| | Card | Type | What it does |
|---|---|---|---|
| <img src="cards/61-assassination.jpg" alt="Assassination" width="132"> | **Assassination**<br><sub>Card 61</sub> | Removal · Any Estate | A courtier anywhere in play leaves play. They go to the discard and may return later as a new person with their printed attributes. |
| <img src="cards/62-targeted-poisoning.jpg" alt="Targeted Poisoning" width="132"> | **Targeted Poisoning**<br><sub>Card 62</sub> | Removal · Any Estate | A courtier anywhere in play leaves play, unless they roll a d6 and survive on an even. A Defense is spent before the roll is made. |
| <img src="cards/63-martyrdom.jpg" alt="Martyrdom" width="132"> | **Martyrdom**<br><sub>Card 63</sub> | Removal · Church | A Church courtier leaves play. They go to the discard and may return later as a new person with their printed attributes. |
| <img src="cards/64-battlefield-betrayal.jpg" alt="Battlefield Betrayal" width="132"> | **Battlefield Betrayal**<br><sub>Card 64</sub> | Removal · Military | A Military courtier leaves play. They go to the discard and may return later as a new person with their printed attributes. |
| <img src="cards/65-bankruptcy.jpg" alt="Bankruptcy" width="132"> | **Bankruptcy**<br><sub>Card 65</sub> | Removal · Merchant | A Merchant courtier leaves play. They go to the discard and may return later as a new person with their printed attributes. |
| <img src="cards/66-mob-violence.jpg" alt="Mob Violence" width="132"> | **Mob Violence**<br><sub>Card 66</sub> | Removal · Commons | A Commons courtier leaves play. They go to the discard and may return later as a new person with their printed attributes. |

## Defense

Attached to an inner-circle courtier ahead of time, paid for by sacrificing a courtier of the named estate from your hand. The estate constrains the *sacrifice*, not the courtier being guarded.

| | Card | Type | What it does |
|---|---|---|---|
| <img src="cards/67-patron-protection.jpg" alt="Patron Protection" width="132"> | **Patron Protection**<br><sub>Card 67</sub> | Defense · Any Estate | Sacrifice a courtier of any estate from your hand and attach this to any inner-circle courtier. It negates the first Removal, Demotion, Strip or Mutation aimed at them, then is discarded. It does not stop an Event. |
| <img src="cards/68-sanctuary.jpg" alt="Sanctuary" width="132"> | **Sanctuary**<br><sub>Card 68</sub> | Defense · Church | Sacrifice a Church courtier from your hand and attach this to any inner-circle courtier. It negates the first Removal, Demotion, Strip or Mutation aimed at them, then is discarded. It does not stop an Event. |
| <img src="cards/69-bodyguard.jpg" alt="Bodyguard" width="132"> | **Bodyguard**<br><sub>Card 69</sub> | Defense · Military | Sacrifice a Military courtier from your hand and attach this to any inner-circle courtier. It negates the first Removal, Demotion, Strip or Mutation aimed at them, then is discarded. It does not stop an Event. |
| <img src="cards/70-deep-pockets.jpg" alt="Deep Pockets" width="132"> | **Deep Pockets**<br><sub>Card 70</sub> | Defense · Merchant | Sacrifice a Merchant courtier from your hand and attach this to any inner-circle courtier. It negates the first Removal, Demotion, Strip or Mutation aimed at them, then is discarded. It does not stop an Event. |
| <img src="cards/71-popularity.jpg" alt="Popularity" width="132"> | **Popularity**<br><sub>Card 71</sub> | Defense · Commons | Sacrifice a Commons courtier from your hand and attach this to any inner-circle courtier. It negates the first Removal, Demotion, Strip or Mutation aimed at them, then is discarded. It does not stop an Event. |

## Strip

Empties an attribute. A strip does not spend the courtier's one mutation, so the slot can be filled again later.

| | Card | Type | What it does |
|---|---|---|---|
| <img src="cards/72-castration.jpg" alt="Castration" width="132"> | **Castration**<br><sub>Card 72</sub> | Strip · Family | A courtier's Family becomes None. They keep their seat. A strip does not spend a mutation, so Adoption can give them a family again. |
| <img src="cards/73-excommunication.jpg" alt="Excommunication" width="132"> | **Excommunication**<br><sub>Card 73</sub> | Strip · Faith | A courtier's Faith becomes None. They keep their seat. A strip does not spend a mutation, so Conversion can bring them to a faith again. |

## Mutation

Changes one attribute. Each attribute may be mutated at most once per courtier.

| | Card | Type | What it does |
|---|---|---|---|
| <img src="cards/74-take-up-the-sword.jpg" alt="Take Up the Sword" width="132"> | **Take Up the Sword**<br><sub>Card 74</sub> | Mutation · Estate | A courtier's Estate becomes Military. If that un-matches the seat they hold, they are demoted to the outer circle at once. |
| <img src="cards/75-take-vows.jpg" alt="Take Vows" width="132"> | **Take Vows**<br><sub>Card 75</sub> | Mutation · Estate | A courtier's Estate becomes Church. If that un-matches the seat they hold, they are demoted to the outer circle at once. |
| <img src="cards/76-enter-trade.jpg" alt="Enter Trade" width="132"> | **Enter Trade**<br><sub>Card 76</sub> | Mutation · Estate | A courtier's Estate becomes Merchant. If that un-matches the seat they hold, they are demoted to the outer circle at once. |
| <img src="cards/77-lose-status.jpg" alt="Lose Status" width="132"> | **Lose Status**<br><sub>Card 77</sub> | Mutation · Estate | A courtier's Estate becomes Commons. If that un-matches the seat they hold, they are demoted to the outer circle at once. |
| <img src="cards/78-conversion.jpg" alt="Conversion" width="132"> | **Conversion**<br><sub>Card 78</sub> | Mutation · Faith | A courtier's Faith becomes any faith but their own; you choose it. A godless or excommunicated courtier may be brought to any of the three. |
| <img src="cards/79-apostasy.jpg" alt="Apostasy" width="132"> | **Apostasy**<br><sub>Card 79</sub> | Mutation · Faith | A courtier's Faith becomes Godless. Godlessness has no agenda, so their seat is one no faith can count. |
| <img src="cards/80-go-native.jpg" alt="Go Native" width="132"> | **Go Native**<br><sub>Card 80</sub> | Mutation · Origin | A courtier's Origin becomes Barbarian. |
| <img src="cards/81-assimilate.jpg" alt="Assimilate" width="132"> | **Assimilate**<br><sub>Card 81</sub> | Mutation · Origin | A courtier's Origin becomes Imperial. |
| <img src="cards/82-adoption.jpg" alt="Adoption" width="132"> | **Adoption**<br><sub>Card 82</sub> | Mutation · Family | Sacrifice a courtier of a family from your hand. The target takes that family as their own. |

## Pivot

Trades your agenda for one out of the pool nobody was dealt.

| | Card | Type | What it does |
|---|---|---|---|
| <img src="cards/83-schismatic-event.jpg" alt="Schismatic Event" width="132"> | **Schismatic Event**<br><sub>Card 83</sub> | Pivot | Discard your agenda and draw a new one from the pool of agendas nobody was dealt. The act is public; both agendas stay private. |

## Outmaneuver

The targeted player loses their next turn, draw included.

| | Card | Type | What it does |
|---|---|---|---|
| <img src="cards/84-outmaneuver.jpg" alt="Outmaneuver" width="132"> | **Outmaneuver**<br><sub>Card 84</sub> | Outmaneuver | The targeted player skips their next turn entirely, draw included. |

## Agenda

Four are dealt face down and four stay in the fog for a Schismatic Event to draw from. The thresholds printed here are the defaults in `succession/agendas.py`; a table running a variant should play off `docs/RULES.md` instead.

| | Card | Type | What it does |
|---|---|---|---|
| <img src="cards/85-house-rising-amonides.jpg" alt="House Rising: Amonides" width="132"> | **House Rising: Amonides**<br><sub>Card 85</sub> | House Amonides | Three or more of the seven inner seats are held by courtiers of House Amonides, at least one of them a Church seat -- the house's own estate. |
| <img src="cards/86-house-rising-mitreas.jpg" alt="House Rising: Mitreas" width="132"> | **House Rising: Mitreas**<br><sub>Card 86</sub> | House Mitreas | Three or more of the seven inner seats are held by courtiers of House Mitreas, at least one of them a Merchant seat -- the house's own estate. |
| <img src="cards/87-house-rising-argaian.jpg" alt="House Rising: Argaian" width="132"> | **House Rising: Argaian**<br><sub>Card 87</sub> | House Argaian | Three or more of the seven inner seats are held by courtiers of House Argaian, at least one of them a Military seat -- the house's own estate. |
| <img src="cards/88-faith-ascendant-old-gods.jpg" alt="Faith Ascendant: Old Gods" width="132"> | **Faith Ascendant: Old Gods**<br><sub>Card 88</sub> | The Old Gods | Four or more of the seven inner seats are held by courtiers of the Old Gods. |
| <img src="cards/89-faith-ascendant-mystery-cults.jpg" alt="Faith Ascendant: Mystery Cults" width="132"> | **Faith Ascendant: Mystery Cults**<br><sub>Card 89</sub> | The Mystery Cults | Four or more of the seven inner seats are held by courtiers of the Mystery Cults. |
| <img src="cards/90-faith-ascendant-the-one-god.jpg" alt="Faith Ascendant: The One God" width="132"> | **Faith Ascendant: The One God**<br><sub>Card 90</sub> | The One God | Four or more of the seven inner seats are held by courtiers of The One God. |
| <img src="cards/91-barbarian-conquest.jpg" alt="Barbarian Conquest" width="132"> | **Barbarian Conquest**<br><sub>Card 91</sub> | The Frontier | Three courtiers of Barbarian origin hold inner seats, in any estates. |
| <img src="cards/92-balance.jpg" alt="Balance" width="132"> | **Balance**<br><sub>Card 92</sub> | The Settlement | Six of the seven seats are filled, and the inner circle shows all three families, all three faiths, and two barbarians at once. |

## Seat

The board: seven chairs, laid out on the table for courtiers to be moved into. Each is bordered in its estate's colour, so a courtier matches its chair by edge alone. Church, Military and Merchant each seat an interchangeable pair; Commons seats one.

| | Card | Type | What it does |
|---|---|---|---|
| <img src="cards/93-seat-archpriest.jpg" alt="Archpriest" width="132"> | **Archpriest**<br><sub>Card 93</sub> | Seat · Church | One of the two Church seats, which are interchangeable. Only a courtier whose current estate is Church may sit here. |
| <img src="cards/94-seat-oracle.jpg" alt="Oracle" width="132"> | **Oracle**<br><sub>Card 94</sub> | Seat · Church | One of the two Church seats, which are interchangeable. Only a courtier whose current estate is Church may sit here. |
| <img src="cards/95-seat-lord-general.jpg" alt="Lord General" width="132"> | **Lord General**<br><sub>Card 95</sub> | Seat · Military | One of the two Military seats, which are interchangeable. Only a courtier whose current estate is Military may sit here. |
| <img src="cards/96-seat-captain-of-the-guard.jpg" alt="Captain of the Guard" width="132"> | **Captain of the Guard**<br><sub>Card 96</sub> | Seat · Military | One of the two Military seats, which are interchangeable. Only a courtier whose current estate is Military may sit here. |
| <img src="cards/97-seat-keeper-of-the-treasury.jpg" alt="Keeper of the Treasury" width="132"> | **Keeper of the Treasury**<br><sub>Card 97</sub> | Seat · Merchant | One of the two Merchant seats, which are interchangeable. Only a courtier whose current estate is Merchant may sit here. |
| <img src="cards/98-seat-master-of-the-market.jpg" alt="Master of the Market" width="132"> | **Master of the Market**<br><sub>Card 98</sub> | Seat · Merchant | One of the two Merchant seats, which are interchangeable. Only a courtier whose current estate is Merchant may sit here. |
| <img src="cards/99-seat-voice-of-the-people.jpg" alt="Voice of the People" width="132"> | **Voice of the People**<br><sub>Card 99</sub> | Seat · Commons | The court's only Commons seat. A house reaches it solely through its charioteer, the one commoner it fields. |

## Card back

Shared by every card in the deck.

| | Card | Type | What it does |
|---|---|---|---|
| <img src="cards/00-cardback.jpg" alt="Card back" width="132"> | **Card back**<br><sub>Card 00</sub> |  | Shared by every card in the deck. |

---

Generated by `python tools/mpcfill.py --profile docs`. Editing this file by hand will not survive the next build -- change `tools/card_text.py` or `tools/cardlist.py` instead.
