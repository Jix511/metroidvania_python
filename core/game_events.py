import pygame

from systems import audio, controls
from systems import settings as settings_system
from systems.items import generate_shop_stock, refresh_price
from systems.spells import AllyShot
from core.game_data import CLASS_ORDER
from core.screen_state import GameScreen, OVERLAY_SCREENS

CLASS_KEYS = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5,
              pygame.K_6)


class GameEventsMixin:
    def handle_events(self):
        mouse_clicked = False
        mouse_right = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._on_keydown(event.key)
            elif event.type == pygame.KEYUP:
                self._on_keyup(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
                elif event.button == 3:
                    mouse_right = True
        if mouse_clicked:
            self._on_click(self._logical_mouse_pos())
        if mouse_right:
            self._on_right_click(self._logical_mouse_pos())
        # Teclado rápido en menú clase
        if self.screen_state is GameScreen.CLASS_MENU:
            keys = pygame.key.get_pressed()
            for idx, class_key in enumerate(CLASS_KEYS):
                if keys[class_key] and idx < len(CLASS_ORDER):
                    self.selected_class = CLASS_ORDER[idx]

    def _any_overlay(self):
        return self.screen_state in OVERLAY_SCREENS

    def _gameplay(self):
        return self.player is not None and self.screen_state is GameScreen.GAMEPLAY

    def _close_top_overlay(self):
        if self.screen_state not in OVERLAY_SCREENS:
            return False
        self.set_screen(GameScreen.GAMEPLAY)
        return True

    def _on_keyup(self, key):
        if controls.key_in('attack', key):
            if self._gameplay() and self.charging > 0:
                self.release_charge()
            else:
                self.charging = 0.0
                self.charge_notified = False
                self.charge_variant = 'neutral'

    def _toggle_overlay(self, state):
        """Abre/cierra un overlay cerrando los demás."""
        opening = self.screen_state is not state
        self.set_screen(state if opening else GameScreen.GAMEPLAY)
        return opening

    def _on_keydown(self, key):
        # Modo reasignación: la próxima tecla se asigna a la acción
        if self.rebinding is not None:
            if key == pygame.K_ESCAPE:
                self.rebinding = None
            else:
                controls.set_binding(self.rebinding, key)
                self.rebinding = None
                audio.play('click')
            return
        if self.screen_state is GameScreen.INTRO:
            if key == pygame.K_ESCAPE:
                self.set_screen(GameScreen.GAMEPLAY)
                self.intro_page = 0
            else:
                self._advance_intro()
            return
        if self.screen_state is GameScreen.DIALOGUE:
            if key == pygame.K_ESCAPE:
                self._close_dialogue()
            elif key in (pygame.K_UP, pygame.K_w):
                self.move_dialogue_choice(-1)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.move_dialogue_choice(1)
            else:
                self.advance_dialogue()
            return
        if key == pygame.K_ESCAPE:
            if self.screen_state is GameScreen.CLASS_MENU:
                self.running = False
            elif self.screen_state is GameScreen.SETTINGS:
                self.rebinding = None
                self.set_screen(GameScreen.PAUSE)
            elif not self._close_top_overlay():
                self.set_screen(GameScreen.PAUSE)
            return
        acts = controls.actions_for(key)
        if not acts and key not in (*CLASS_KEYS, pygame.K_l):
            return
        if self.screen_state is GameScreen.PAUSE:
            return  # en pausa solo ratón y ESC
        if self.screen_state is GameScreen.SETTINGS:
            return
        if 'attack' in acts and self._gameplay():
            self.charging = max(self.charging, 0.001)
            self.charge_variant = self.attack_variant()
            return
        if key in CLASS_KEYS:
            if self.screen_state is GameScreen.CLASS_MENU:
                idx = CLASS_KEYS.index(key)
                if idx < len(CLASS_ORDER):
                    self.selected_class = CLASS_ORDER[idx]
            return
        if 'jump' in acts:
            if self.player and self.screen_state is GameScreen.GAMEPLAY:
                self.player.try_double_jump()
            return
        if 'confirm' in acts:
            if self.screen_state is GameScreen.GAME_OVER:
                self.respawn()
            elif self.screen_state is GameScreen.SKILLS and self.player:
                self.player.respec_all_skills()
                audio.play('click')
            return
        if 'classes' in acts:
            if self.screen_state not in (GameScreen.CLASS_MENU, GameScreen.GAME_OVER):
                self.set_screen(GameScreen.CLASS_MENU)
            return
        if 'skills' in acts:
            if self.screen_state not in (GameScreen.CLASS_MENU, GameScreen.GAME_OVER) and self.player:
                self._toggle_overlay(GameScreen.SKILLS)
            return
        if 'inventory' in acts:
            if self.screen_state not in (GameScreen.CLASS_MENU, GameScreen.GAME_OVER) and self.player:
                self._toggle_overlay(GameScreen.INVENTORY)
            return
        if 'travel' in acts:
            if self.screen_state not in (GameScreen.CLASS_MENU, GameScreen.GAME_OVER) and self.player:
                self._toggle_overlay(GameScreen.TRAVEL)
            return
        if 'map' in acts:
            if self.screen_state not in (GameScreen.CLASS_MENU, GameScreen.GAME_OVER) and self.player:
                opening = self._toggle_overlay(GameScreen.MAP)
                if opening:
                    self.map_selected_zone = self.current_zone
            return
        if 'journal' in acts:
            if self.screen_state not in (GameScreen.CLASS_MENU, GameScreen.GAME_OVER) and self.player:
                self._toggle_overlay(GameScreen.BESTIARY)
            return
        if 'quests' in acts:
            if self.screen_state not in (GameScreen.CLASS_MENU, GameScreen.GAME_OVER) and self.player:
                self._toggle_overlay(GameScreen.QUESTS)
            return
        if not self._gameplay():
            return
        if 'shop' in acts:
            npc_id = self.nearest_npc()
            if npc_id:
                self.interact_npc(npc_id)
        elif 'potion' in acts:
            if self.player.drink_potion():
                self.inv_message = "Poción: +40% vida"
                self.inv_message_t = 1.5
                audio.play('potion')
                self.fx.burst(self.player.rect.centerx, self.player.rect.centery, n=12,
                                color=(120, 255, 140), speed=130.0, life=0.5, grav=100.0)
        elif 'mute' in acts:
            muted = audio.toggle_mute()
            if self.music is not None:
                try:
                    self.music.set_muted(muted)
                except Exception:
                    pass
            self.inv_message = "Sonido: OFF" if muted else "Sonido: ON"
            self.inv_message_t = 1.5
        elif 'teleport' in acts:
            route_id = self.game_map.try_route_teleport(self.player)
            if route_id or self.player.try_teleport(self.game_map):
                self.charging = 0.0
                self.charge_notified = False
                self.inv_message = ("Ancla rúnica enlazada" if route_id
                                    else "Teletransporte")
                self.inv_message_t = 1.0
                audio.play('teleport')
                self.fx.burst(self.player.rect.centerx, self.player.rect.centery, n=14,
                            color=(200, 120, 255), speed=180.0, life=0.4, grav=0.0)
        elif 'dash' in acts:
            if self.player.try_dash():
                self.charging = 0.0
                self.charge_notified = False
                audio.play('dash', 0.8)
        elif 'parry' in acts:
            if self.try_execute():
                return
            if self.player.begin_parry():
                audio.play('block', 0.45)
                self.fx.burst(self.player.rect.centerx, self.player.rect.centery,
                              n=5, color=(175, 220, 255), speed=80.0,
                              life=0.18, grav=0.0)
            elif self.player.try_backflip():
                # Voltereta del arquero: dispara hacia atrás al saltar
                back = -1 if self.player.facing_right else 1
                sx, sy = self.player.weapon_origin(
                    self.player.rect.centerx + back * 100, self.player.rect.centery)
                self.ally_shots.add(AllyShot(sx, sy, back * 480.0, 0, self.player.damage,
                                            radius=4, life=1.2, color=(200, 230, 150),
                                            pierce=self.player.skill_ranks.get('piercing', 0),
                                            visual='arrow', element='physical'))
                audio.play('dash', 0.8)
        elif 'ngplus' in acts:
            if self.boss is None and self.completed():
                self.start_ng_plus()
        elif 'nova' in acts:
            self.cast_nova()
        elif 'meteor' in acts:
            wx, wy = self._mouse_world()
            self.cast_meteor(wx, wy)
        elif 'blizzard' in acts:
            wx, wy = self._mouse_world()
            self.cast_blizzard(wx, wy)
        elif 'whirlwind' in acts:
            self.cast_whirlwind()
        elif key == pygame.K_l:
            if self.screen_state is GameScreen.CLASS_MENU:
                self.try_load_save()

    def _on_pause_click(self, pos):
        act = self.ui.pause_action_at(pos)
        if act is None:
            return
        kind, arg = act
        audio.play('click', 0.7)
        if kind == 'resume':
            self.set_screen(GameScreen.GAMEPLAY)
        elif kind == 'save':
            if self.player:
                self.player.save_game()
                self.inv_message = "Partida guardada"
                self.inv_message_t = 2.0
        elif kind == 'settings':
            self.settings_tab = 'graphics'
            self.set_screen(GameScreen.SETTINGS)
        elif kind == 'achievements':
            self.set_screen(GameScreen.ACHIEVEMENTS)
        elif kind == 'classes':
            self.set_screen(GameScreen.CLASS_MENU)
        elif kind == 'quit':
            if self.player:
                self.player.save_game()
            self.running = False

    def _on_settings_click(self, pos):
        action = self.ui.settings_action_at(pos, self.settings_tab)
        if action is None:
            return
        kind, value = action
        audio.play('click', 0.7)
        if kind == 'tab':
            self.settings_tab = value
            self.rebinding = None
        elif kind == 'back':
            self.rebinding = None
            self.set_screen(GameScreen.PAUSE)
        elif kind == 'resolution':
            settings_system.cycle_resolution(self.settings)
            settings_system.save(self.settings)
            self._apply_display_settings()
        elif kind == 'fullscreen':
            self.settings['fullscreen'] = not self.settings['fullscreen']
            settings_system.save(self.settings)
            self._apply_display_settings()
        elif kind == 'effects_quality':
            settings_system.cycle_effects_quality(self.settings)
            settings_system.save(self.settings)
        elif kind == 'minimap_mode':
            settings_system.cycle_minimap_mode(self.settings)
            settings_system.save(self.settings)
        elif kind == 'volume':
            key, amount = value
            settings_system.adjust_volume(self.settings, key, amount)
            settings_system.save(self.settings)
            self._apply_audio_settings()
        elif kind == 'accessibility':
            if value == 'text_size':
                settings_system.cycle_text_size(self.settings)
            elif value == 'screen_shake':
                settings_system.cycle_screen_shake(self.settings)
            else:
                self.settings[value] = not self.settings.get(value, False)
            settings_system.save(self.settings)
            self._apply_accessibility_settings()
        elif kind == 'rebind':
            self.rebinding = value
        elif kind == 'reset_settings':
            self.settings = settings_system.reset()
            controls.reset_defaults()
            self.rebinding = None
            self._apply_audio_settings()
            self._apply_display_settings()
            self._apply_accessibility_settings()

    def _on_right_click(self, pos):
        """Click derecho contextual según la especialidad de la clase."""
        p = self.player
        if p is None or self.screen_state is not GameScreen.GAMEPLAY:
            return
        if p.character_class == 'reaper':
            wx, wy = self._mouse_world()
            self.cast_soul_reap(wx, wy)
        elif p.character_class == 'kitsune':
            wx, wy = self._mouse_world()
            if 'nine_tail_burst' in p.unlocked_abilities:
                self.cast_nine_tail_burst(wx, wy)
            else:
                self.fire_foxfire(wx, wy, empowered=True)
        elif 'death_mark' in p.unlocked_abilities:
            self._try_mark(pos)
        elif 'triple_shot' in p.unlocked_abilities:
            wx, wy = self._mouse_world()
            self.cast_triple(wx, wy)
        elif 'fireball' in p.unlocked_abilities:
            wx, wy = self._mouse_world()
            self.cast_fireball(wx, wy)

    def _try_mark(self, pos):
        """Marca de muerte sobre el enemigo bajo el cursor."""
        p = self.player
        if self.mark_cd > 0:
            return
        wx = pos[0] - self.camera.camera.x
        wy = pos[1] - self.camera.camera.y
        for e in self.enemies:
            if e.rect.collidepoint(wx, wy):
                dx = e.rect.centerx - p.rect.centerx
                dy = e.rect.centery - p.rect.centery
                if dx * dx + dy * dy > 380 * 380:
                    self.inv_message = "Demasiado lejos para marcar"
                    self.inv_message_t = 1.5
                    return
                e.status.apply('mark', 5.0)
                self.mark_cd = 8.0
                self.texts.add(e.rect.centerx, e.rect.top - 6, "¡MARCADO!", (255, 70, 70))
                self.fx.burst(e.rect.centerx, e.rect.centery, n=10, color=(255, 70, 70),
                              speed=150.0, life=0.4, grav=0.0)
                audio.play('skill', 0.8)
                return

    def _advance_intro(self):
        pages = self.intro_pages()
        self.intro_page += 1
        audio.play('click', 0.7)
        if self.intro_page >= len(pages):
            self.set_screen(GameScreen.GAMEPLAY)
            self.intro_page = 0

    def _on_click(self, pos):
        if self.screen_state is GameScreen.INTRO:
            self._advance_intro()
            return
        if self.screen_state is GameScreen.DIALOGUE:
            self.advance_dialogue()
            return
        if self.screen_state is GameScreen.CLASS_MENU:
            idx = self.ui.class_card_at(pos)
            if idx is not None and idx < len(CLASS_ORDER):
                self.selected_class = CLASS_ORDER[idx]
                self.create_player(self.selected_class)
                audio.play('click')
        elif self.screen_state is GameScreen.PAUSE:
            self._on_pause_click(pos)
        elif self.screen_state is GameScreen.SETTINGS:
            self._on_settings_click(pos)
        elif self.screen_state is GameScreen.SHOP and self.player:
            act = self.ui.shop_action_at(self.player, self.shop_stock, pos, self.shop_tab)
            if act is None:
                return
            kind, arg = act
            if kind == 'tab':
                self.shop_tab = arg
                audio.play('click', 0.6)
            elif kind == 'buy':
                gold0 = self.player.gold
                self._shop_buy(arg)
                if self.player.gold < gold0:
                    audio.play('buy')
            elif kind == 'sell':
                self._shop_sell(arg)
                audio.play('sell', 0.8)
            elif kind == 'upgrade':
                self._shop_upgrade(arg)
            elif kind == 'craft':
                slot, rarity = arg
                self._shop_craft(slot, rarity)
            elif kind == 'potion':
                ok, msg = self.player.buy_potion()
                self.inv_message, self.inv_message_t = msg, 2.0
                if ok:
                    audio.play('buy', 0.8)
            elif kind == 'refresh':
                cost = refresh_price(self.player.level)
                if self.player.spend_gold(cost):
                    self.shop_stock = generate_shop_stock(self.player.level, luck=self._shop_luck())
                    self.shop_level = self.player.level
                    self.inv_message = f"Surtido renovado (-{cost}g)"
                    audio.play('click')
                else:
                    self.inv_message = f"Oro insuficiente ({cost}g)"
                self.inv_message_t = 2.0
        elif self.screen_state is GameScreen.TRAVEL and self.player:
            cp_id = self.ui.travel_item_at(self.player, self.game_map.checkpoints, pos)
            if cp_id:
                self.fast_travel(cp_id)
        elif self.screen_state is GameScreen.MAP and self.player:
            action = self.ui.world_map_action_at(self.player, pos)
            if action is None:
                return
            kind, value = action
            if kind == 'zone':
                self.map_selected_zone = value
                audio.play('click', 0.6)
            elif kind == 'travel':
                self.fast_travel(value)
        elif self.screen_state is GameScreen.BESTIARY:
            cat = self.ui.bestiary_tab_at(pos)
            if cat:
                self.bestiary_tab = cat
                audio.play('click', 0.6)
        elif self.screen_state is GameScreen.INVENTORY and self.player:
            # Click en inventario: equipar / desequipar
            inv_id = self.ui.inventory_item_at(self.player, pos)
            if inv_id:
                ok, msg = self.player.equip_item(inv_id)
                self.inv_message, self.inv_message_t = msg, 2.0
                return
            slot = self.ui.equipped_slot_at(pos)
            if slot:
                ok, msg = self.player.unequip_slot(slot)
                self.inv_message, self.inv_message_t = msg, 2.0
                return
        elif self.screen_state is GameScreen.SKILLS and self.player:
            cat = self.ui.skill_tab_at(pos)
            if cat:
                self.player.skill_tree_selected_category = cat
                audio.play('click', 0.6)
                return
            sid = self.ui.skill_button_at(self.player, pos)
            if sid:
                ok, msg = self.player.buy_skill(sid)
                if ok:
                    audio.play('skill')
                else:
                    audio.play('click', 0.5)

    # --- Hechizos del mago ---

    def _mouse_world(self):
        mx, my = self._logical_mouse_pos()
        return (mx - self.camera.camera.x, my - self.camera.camera.y)
