"""Single source of truth for the active game screen."""

from enum import Enum, auto


class GameScreen(Enum):
    CLASS_MENU = auto()
    INTRO = auto()
    GAMEPLAY = auto()
    SKILLS = auto()
    INVENTORY = auto()
    TRAVEL = auto()
    MAP = auto()
    BESTIARY = auto()
    QUESTS = auto()
    DIALOGUE = auto()
    SHOP = auto()
    PAUSE = auto()
    SETTINGS = auto()
    ACHIEVEMENTS = auto()
    GAME_OVER = auto()


OVERLAY_SCREENS = frozenset({
    GameScreen.SKILLS,
    GameScreen.INVENTORY,
    GameScreen.TRAVEL,
    GameScreen.MAP,
    GameScreen.BESTIARY,
    GameScreen.QUESTS,
    GameScreen.DIALOGUE,
    GameScreen.SHOP,
    GameScreen.PAUSE,
    GameScreen.SETTINGS,
    GameScreen.ACHIEVEMENTS,
})


class ScreenStateMixin:
    """Owns transitions for the single active game screen."""

    screen_state: GameScreen

    def set_screen(self, state):
        if not isinstance(state, GameScreen):
            raise TypeError(f'Invalid game screen: {state!r}')
        self.screen_state = state
