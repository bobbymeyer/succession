"""Court of Succession -- a headless simulator for the card-driven court game.

Public entry points::

    from succession import Config, play_game, make_bot
    result = play_game(Config(), seed=1, bot_factory=lambda t, s, r: make_bot(t, s, r))

or from the command line::

    python -m succession run --games 500 --out results.csv --summary
"""

from .agendas import AGENDAS, AGENDAS_BY_KEY, Agenda
from .bots import BOT_TIERS, make_bot
from .cards import build_cards
from .courtiers import COURTIERS
from .engine import GameResult, play_game, setup_game
from .session import GameSession
from .state import Config, GameState

__all__ = [
    "AGENDAS",
    "AGENDAS_BY_KEY",
    "Agenda",
    "BOT_TIERS",
    "COURTIERS",
    "Config",
    "GameResult",
    "GameSession",
    "GameState",
    "build_cards",
    "make_bot",
    "play_game",
    "setup_game",
]
__version__ = "0.1.0a1"  # playtest alpha
