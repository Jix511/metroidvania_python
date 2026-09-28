"""Adaptive music state selection."""

from core.screen_state import GameScreen


class GameAudioMixin:
    def _update_music(self, dt):
        if self.music is None:
            return
        paused = (self.player is None or self.screen_state in {
            GameScreen.CLASS_MENU,
            GameScreen.INTRO,
            GameScreen.PAUSE,
            GameScreen.SETTINGS,
        })
        if paused:
            self.music.set_mode('explore', menu=True)
        elif self.boss is not None or self.pending_boss_defeat is not None:
            self.music.set_mode('boss')
            if self.boss is not None and hasattr(self.music, 'set_boss_phase'):
                self.music.set_boss_phase(self.boss.phase)
        elif self.combat_timer > 0 or self._enemy_near(420):
            self.music.set_mode('combat')
        else:
            self.music.set_mode('explore')
        self.music.update(dt)

    def _enemy_near(self, radius):
        if self.player is None:
            return False
        r2 = radius * radius
        for e in self.enemies:
            dx = e.rect.centerx - self.player.rect.centerx
            dy = e.rect.centery - self.player.rect.centery
            if dx * dx + dy * dy <= r2:
                return True
        return False
