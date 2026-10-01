# Court of Succession — playtest alpha

The King has died, leaving his infant son to inherit the throne. You are one
of the powerful men of the empire, intriguing for the ear of the young
monarch: place your agents in the offices close to the king, and see your
faction's secret agenda through before anyone else sees theirs.

A card game for 2–8 players. Every player holds a hidden agenda — a faith
to raise, a house to put in power, a balance to keep — and the court of seven
seats is shared, so a courtier you seat may serve a rival's agenda as well as
your own.

## Play it

**[Play in your browser](https://bobbymeyer.github.io/succession/)** against
bots, on a phone or a computer. Nothing to install; on a phone it can be added
to your home screen and plays offline. Your first game deals you a gentle
hand, and **Rules** in the game has the whole of how to play.

**Print it** for a real table:

- [The deck](docs/CARDS.md) — every card, with its picture and rules text.
- [Download the print-ready deck](https://github.com/bobbymeyer/succession/releases/latest/download/succession-print-deck.zip)
  — sized and bled for MakePlayingCards, with an order file that fills
  itself in. [docs/PRINTING.md](docs/PRINTING.md) walks through it.
- The board prints at home: [A4](docs/board-a4.pdf) or
  [Letter](docs/board-letter.pdf), two pages; cut out the seven seats.

## Tell us how it went

This is a playtest, and what we most need is to hear from people who played.

- **[Send a playtest report](https://github.com/bobbymeyer/succession/issues/new?template=playtest.yml)**
  — a short form: who won, how long it took, what confused you, whether you'd
  play again. At the end of a browser game, **Tell us how it went** opens it
  with your game already filled in.
- **[Report a problem](https://github.com/bobbymeyer/succession/issues/new?template=bug.yml)**
  — something broke, or a card didn't do what it said. The link at the foot
  of the game's page fills in which build you're on. A game record (end
  screen → *Save this game*) lets us replay exactly what you saw.

Both need a GitHub account.

## Where it stands

The rules are settled enough to put in front of players: every agenda is
winnable, the eight of them win within seven points of each other, and 24,000
simulated games resolve without a stall. What is alpha about it is that the
numbers come from bots; the open questions in [docs/RULES.md](docs/RULES.md)
are the ones a real table will answer faster than a batch run.

The game changes as the playtest goes. The build named at the foot of the
page is the version you played, and a saved game replays only under the rules
it was played by.

## For developers

The rules engine is a dependency-free Python package (`succession/`), and the
browser game runs that same package in the page under Pyodide, so a bot, a
terminal player and a browser player all play the identical game.

```bash
python -m succession play                     # take a seat against the bots in a terminal
python -m succession run --games 1000 --summary
cd web && npm install && npm run dev          # the browser game at http://localhost:5173
```

- [docs/DEVELOPING.md](docs/DEVELOPING.md) — the code, the simulator, the
  print tooling and the browser game.
- [docs/RULES.md](docs/RULES.md) — the rules as implemented, every assumption
  and the flag that flips it. Read it before changing anything.
- [docs/BALANCE.md](docs/BALANCE.md) — what the batch runs found.
- [docs/EMBED.md](docs/EMBED.md) — putting the game on another site.
