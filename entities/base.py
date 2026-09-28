"""Shared object-oriented behavior for living world entities."""

import random

import pygame


class CombatEntity(pygame.sprite.Sprite):
    """Sprite with shared animation and combat-feedback state."""

    def __init__(self):
        super().__init__()
        self.anim_t = 0.0
        self.anim_phase = random.uniform(0.0, 0.7)
        self.visual_anim_state = None
        self.visual_anim_started = 0.0
        self.fx_texts = []
        self.posture_max = 0.0
        self.posture = 0.0
        self.posture_broken_t = 0.0
        self.posture_regen_delay = 0.0
        self.posture_resist_t = 0.0

    @property
    def health_ratio(self):
        return self.health / max(1, self.max_health)

    @property
    def defeated(self):
        return self.health <= 0

    def queue_fx_text(self, value, color):
        self.fx_texts.append((float(value), color))

    def drain_fx_texts(self):
        pending = list(self.fx_texts)
        self.fx_texts.clear()
        return pending

    def init_posture(self, amount):
        self.posture_max = max(1.0, float(amount))
        self.posture = self.posture_max

    def damage_posture(self, amount):
        if self.posture_max <= 0 or self.posture_broken_t > 0:
            return False
        resistance = 0.55 if self.posture_resist_t > 0 else 1.0
        self.posture = max(0.0, self.posture - max(0.0, float(amount)) * resistance)
        self.posture_regen_delay = 2.0
        if self.posture <= 0:
            self.posture_broken_t = 1.5 if getattr(self, 'boss_id', None) else 2.2
            return True
        return False

    def update_posture(self, dt):
        self.posture_resist_t = max(0.0, self.posture_resist_t - dt)
        if self.posture_max <= 0:
            return
        if self.posture_broken_t > 0:
            self.posture_broken_t = max(0.0, self.posture_broken_t - dt)
            if self.posture_broken_t <= 0:
                self.posture = self.posture_max
            return
        self.posture_regen_delay = max(0.0, self.posture_regen_delay - dt)
        if self.posture_regen_delay <= 0 and self.posture < self.posture_max:
            self.posture = min(self.posture_max, self.posture + self.posture_max * 0.22 * dt)
