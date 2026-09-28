import unittest

from core.screen_state import GameScreen, OVERLAY_SCREENS, ScreenStateMixin


class ScreenStateTests(unittest.TestCase):
    def setUp(self):
        self.state = ScreenStateMixin()
        self.state.screen_state = GameScreen.CLASS_MENU

    def test_transition_replaces_previous_screen(self):
        self.state.set_screen(GameScreen.GAMEPLAY)
        self.state.set_screen(GameScreen.INVENTORY)

        self.assertIs(self.state.screen_state, GameScreen.INVENTORY)
        self.assertNotEqual(self.state.screen_state, GameScreen.GAMEPLAY)

    def test_overlay_collection_contains_only_overlay_screens(self):
        self.assertIn(GameScreen.PAUSE, OVERLAY_SCREENS)
        self.assertIn(GameScreen.SHOP, OVERLAY_SCREENS)
        self.assertNotIn(GameScreen.GAMEPLAY, OVERLAY_SCREENS)
        self.assertNotIn(GameScreen.GAME_OVER, OVERLAY_SCREENS)

    def test_invalid_screen_is_rejected(self):
        with self.assertRaises(TypeError):
            self.state.set_screen('inventory')


if __name__ == '__main__':
    unittest.main()
