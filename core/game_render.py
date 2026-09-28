import pygame

from systems import audio
import math
from entities.boss import Boss
from constants import (
    CHARACTER_CLASSES,
    COLORS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TILE_SIZE,
)
from systems.items import RARITIES
from systems.balance_data import BOSS_DEFS
from systems.npc_data import NPCS, npc_position, refuge_members
from systems.secret_data import SECRETS
from world.tilemap import tutorial_signs
from world.world_data import BOUNDARIES
from core.screen_state import GameScreen, OVERLAY_SCREENS
from presentation.animation import add_secondary_motion, pick_frame, state_elapsed
from presentation.death_effects import draw_death_echo
from systems.spatial import near_view


class GameRenderMixin:
    def draw(self):
        if self.screen_state is GameScreen.CLASS_MENU:
            self.ui.draw_class_menu(CHARACTER_CLASSES, self.save_exists)
            return
        if self.screen_state is GameScreen.INTRO:
            self.draw_world()
            self.ui.draw_intro(self.intro_pages()[self.intro_page], self.intro_page + 1,
                                len(self.intro_pages()))
            return
        if self.screen_state in OVERLAY_SCREENS or self.screen_state is GameScreen.GAME_OVER:
            self.draw_world()
            self.ui.draw_game_ui(self.player, self.game_map.get_zone_at(self.player.rect.centerx)['name'], self.gate_prompt, self.shop_prompt)
            self.ui.draw_minimap(self.player, self.enemies, self.current_room,
                                 self.settings.get('minimap_mode', 'full'))
            if self.boss is not None:
                self.ui.draw_boss_bar(self.boss)
            if self.screen_state is GameScreen.GAME_OVER:
                self.ui.draw_game_over()
            elif self.screen_state is GameScreen.PAUSE:
                self.ui.draw_pause(self.player)
            elif self.screen_state is GameScreen.SETTINGS:
                self.ui.draw_settings(self.settings, self.settings_tab, self.rebinding)
            elif self.screen_state is GameScreen.ACHIEVEMENTS:
                self.ui.draw_achievements(self.player)
            elif self.screen_state is GameScreen.SKILLS:
                self.ui.draw_skill_tree(self.player)
            elif self.screen_state is GameScreen.INVENTORY:
                self.ui.draw_inventory(self.player, self.inv_message if self.inv_message_t > 0 else "")
            elif self.screen_state is GameScreen.TRAVEL:
                self.ui.draw_travel_menu(self.player, self.game_map.checkpoints)
            elif self.screen_state is GameScreen.MAP:
                self.ui.draw_world_map(self.player, self.map_selected_zone)
            elif self.screen_state is GameScreen.BESTIARY:
                self.ui.draw_bestiary(self.player, self.bestiary_tab)
            elif self.screen_state is GameScreen.QUESTS:
                self.ui.draw_quest_journal(self.player)
            elif self.screen_state is GameScreen.DIALOGUE:
                line = self.dialogue_pages[self.dialogue_page]
                visible = int((pygame.time.get_ticks() - self.dialogue_started_at) * 0.05)
                npc = NPCS[self.dialogue_npc_id]
                self.ui.draw_dialogue(npc['name'], line[:visible],
                                      self.dialogue_page + 1, len(self.dialogue_pages),
                                      npc['color'], self.dialogue_choices,
                                      self.dialogue_choice)
            elif self.screen_state is GameScreen.SHOP:
                self.ui.draw_shop(self.player, self.shop_stock, self.shop_tab)
            return
        self.draw_world()
        self.ui.draw_game_ui(self.player, self.game_map.get_zone_at(self.player.rect.centerx)['name'], self.gate_prompt, self.shop_prompt)
        self.ui.draw_minimap(self.player, self.enemies, self.current_room,
                             self.settings.get('minimap_mode', 'full'))
        if self.boss is not None:
            self.ui.draw_boss_bar(self.boss)
        if self.boss_banner_t > 0 and self.boss is not None:
            t = self.font_title.render(self.boss.name.upper(), True, (255, 80, 80))
            self.screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 120))
        if self.boss_phase_t > 0 and self.boss_phase_text:
            t = self.font_big.render(self.boss_phase_text, True, self.boss_phase_color)
            self.screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 155))
        self._draw_boss_cinematic()
        if self.victory_t > 0:
            t = self.font_title.render(self.victory_text.split('!')[0].strip('¡') if self.victory_text else "VICTORIA", True, COLORS['YELLOW'])
            self.screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 120))
        if self.zone_banner_t > 0 and self.zone_banner:
            t = self.font_title.render(self.zone_banner, True, COLORS['WHITE'])
            self.screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 120))
        if self.inv_message_t > 0 and self.inv_message:
            t = self.font_small.render(self.inv_message, True, COLORS['YELLOW'])
            self.screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 90))
        if self.route_prompt:
            t = self.font_small.render(self.route_prompt, True, (175, 225, 255))
            self.screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 210))
        # Objetivo actual (se oculta con jefe en pantalla)
        if self.boss is None:
            obj = self.current_objective()
            if obj:
                t = self.font_small.render(f"Objetivo: {obj}", True, (180, 220, 255))
                self.screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 58))
        # Cartel del tutorial
        if self.sign_text:
            t = self.font.render(self.sign_text, True, COLORS['WHITE'])
            bg = pygame.Surface((t.get_width() + 20, t.get_height() + 10))
            bg.fill((20, 20, 30))
            bg.set_alpha(220)
            bx = SCREEN_WIDTH // 2 - bg.get_width() // 2
            self.screen.blit(bg, (bx, SCREEN_HEIGHT - 60))
            self.screen.blit(t, (bx + 10, SCREEN_HEIGHT - 55))

    def draw_world(self):
        off = self.camera.get_render_offset()
        ox, oy = int(off[0]), int(off[1])
        view_center = (-ox + SCREEN_WIDTH // 2, -oy + SCREEN_HEIGHT // 2)
        visible_sprites = [spr for spr in self.all_sprites
                           if near_view(spr.rect, view_center, SCREEN_WIDTH, SCREEN_HEIGHT, 100)]
        zone_id = self.current_zone or self.game_map.get_zone_at(
            self.player.rect.centerx if self.player else 0)['id']
        quality = ('low' if self.settings.get('reduced_motion')
                   else self.settings.get('effects_quality', 'high'))
        background_zone, transition = self._biome_transition(zone_id)
        self.environment.draw_background(
            self.screen, self.camera.camera.x, background_zone, quality,
            transition=transition,
            boss_id=self.boss.boss_id if self.boss is not None else None)
        self.game_map.draw(self.screen, off)
        for platform in self.moving_platforms:
            platform.draw(self.screen, off)
        self.fx.draw(self.screen, off, max_layer=0)
        self._draw_ability_routes(ox, oy)
        self._draw_restored_biome(ox, oy)
        self._draw_reward_altar(ox, oy)
        self._draw_refuge(ox, oy)
        # NPC del mundo
        base_npc = self.art_assets.get('shopkeeper')
        for npc_id, npc in NPCS.items():
            npc_x, npc_y = npc_position(self.player, npc)
            sx, sy = int(npc_x) + ox, int(npc_y) + oy
            if base_npc is not None:
                image = base_npc.copy()
                if npc_id != 'maela':
                    tint = pygame.Surface(image.get_size(), pygame.SRCALPHA)
                    tint.fill((*npc['color'], 255))
                    image.blit(tint, (0, 0), special_flags=pygame.BLEND_MULT)
                self.screen.blit(image, image.get_rect(midbottom=(sx, sy)))
            else:
                pygame.draw.rect(self.screen, npc['color'],
                                 pygame.Rect(sx - 10, sy - 30, 20, 30), border_radius=3)
                pygame.draw.circle(self.screen, npc['color'], (sx, sy - 38), 9)
            if npc['role'] == 'shopkeeper':
                sign = self.font.render('$', True, COLORS['YELLOW'])
                self.screen.blit(sign, (sx - sign.get_width() // 2, sy - 52))
            marker = self.npc_quest_marker(npc_id) if self.player is not None else None
            if marker:
                symbol = '?' if marker == 'available' else '!'
                color = (255, 220, 80) if marker == 'available' else (100, 255, 150)
                quest_mark = self.font_big.render(symbol, True, color)
                self.screen.blit(quest_mark, (sx - quest_mark.get_width() // 2, sy - 82))
        # Grietas de paredes falsas y cofres secretos descubiertos.
        if self.player is not None:
            for secret_id, secret in SECRETS.items():
                wall = secret['wall']
                if secret_id not in self.player.discovered_secrets:
                    x = wall['tx'] * TILE_SIZE + ox
                    y = wall['y0'] * TILE_SIZE + oy
                    h = (wall['y1'] - wall['y0'] + 1) * TILE_SIZE
                    pygame.draw.line(self.screen, (110, 150, 155),
                                     (x + 6, y + 4), (x + 10, y + h // 2), 1)
                    pygame.draw.line(self.screen, (110, 150, 155),
                                     (x + 10, y + h // 2), (x + 5, y + h - 5), 1)
                    continue
                chest = secret['chest']
                cx = chest['tx'] * TILE_SIZE + TILE_SIZE // 2 + ox
                cy = chest['ty'] * TILE_SIZE + TILE_SIZE + oy
                opened = secret_id in self.player.opened_secret_chests
                body = pygame.Rect(cx - 11, cy - 13, 22, 13)
                pygame.draw.rect(self.screen, (75, 65, 58) if opened else (165, 105, 42),
                                 body, border_radius=2)
                pygame.draw.rect(self.screen, (235, 195, 75) if not opened else (95, 90, 85),
                                 body, 2, border_radius=2)
                if not opened:
                    pygame.draw.circle(self.screen, (255, 225, 110), (cx, cy - 7), 2)
        # Checkpoints: obeliscos (cian desbloqueado, dorado = base activa, gris = bloqueado)
        if self.player is not None:
            rp = self.player.respawn_point
            for cp in self.game_map.checkpoints:
                r = cp['rect'].move((ox, oy))
                if cp['id'] in self.player.unlocked_checkpoints:
                    col = (100, 220, 255)
                    if rp and abs(rp[0] - (cp['rect'].x - 24)) < 4:
                        col = (255, 220, 100)
                else:
                    col = (90, 90, 100)
                if cp['id'] in self.player.unlocked_checkpoints:
                    pulse = 18 + int(3 * math.sin(pygame.time.get_ticks() * 0.005))
                    halo = pygame.Surface((pulse * 2, pulse * 2), pygame.SRCALPHA)
                    pygame.draw.circle(halo, (*col, 55), (pulse, pulse), pulse)
                    self.screen.blit(halo, halo.get_rect(center=r.center))
                pygame.draw.rect(self.screen, col, r, border_radius=4)
                pygame.draw.rect(self.screen, COLORS['BLACK'], r, 1, border_radius=4)
                pygame.draw.rect(self.screen, COLORS['WHITE'],
                                pygame.Rect(r.x + 4, r.y + 5, r.w - 8, 8), border_radius=2)
        # Carteles del tutorial (postes de madera con !)
        for sign in tutorial_signs():
            sx = sign['tx'] * TILE_SIZE + ox
            sy = (self.game_map.height - BOUNDARIES['floor_depth']) * TILE_SIZE + oy
            pygame.draw.rect(self.screen, (120, 85, 40), pygame.Rect(sx - 2, sy - 34, 4, 34))
            pygame.draw.rect(self.screen, (150, 110, 55), pygame.Rect(sx - 11, sy - 52, 22, 20), border_radius=2)
            mark = self.font.render("!", True, COLORS['BLACK'])
            self.screen.blit(mark, (sx - mark.get_width() // 2, sy - 52))
        # Drops
        for d in self.drops:
            if not near_view(d['rect'], view_center, SCREEN_WIDTH, SCREEN_HEIGHT, 50):
                continue
            r = d['rect'].move((ox, oy))
            if d['item'] is not None:
                col = RARITIES.get(d['item']['rarity'], {}).get('color', (255, 255, 255))
                icon = self.ui._item_icon(d['item'])
            else:
                col = (255, 220, 100)  # solo oro
                icon = None
            if icon is not None:
                small = pygame.transform.scale(icon, (20, 20))
                self.screen.blit(small, small.get_rect(center=r.center))
                pygame.draw.rect(self.screen, col, r.inflate(6, 6), 1, border_radius=3)
            else:
                pygame.draw.rect(self.screen, col, r, border_radius=3)
                pygame.draw.rect(self.screen, COLORS['BLACK'], r, 1, border_radius=3)
        # Sombras de contacto: fijan visualmente actores y NPC al terreno.
        for spr in visible_sprites:
            center = (spr.rect.centerx + ox, spr.rect.bottom + oy + 2)
            airborne = not getattr(spr, 'on_ground', True) and not getattr(spr, 'flying', False)
            width = max(16, min(70, getattr(spr.rect, 'width', 16) * 2))
            self.environment.draw_contact_shadow(self.screen, center, width, airborne)
        for spr in visible_sprites:
            img, flip, scale = self._entity_frame(spr)
            if flip:
                img = pygame.transform.flip(img, True, False)
            if scale != 1.0:
                img = pygame.transform.scale(img, (max(1, int(img.get_width() * scale)),
                                                   max(1, int(img.get_height() * scale))))
            # Flash blanco: telegraph de jefe o impacto recibido
            if getattr(spr, 'flash_t', 0) > 0 or getattr(spr, 'hit_flash', 0) > 0:
                img = self._white_copy(img)
            elif spr is not self.player:
                # Tinte según estado (quemado/veneno/slow/stun)
                tint = getattr(getattr(spr, 'status', None), 'tint', lambda: None)()
                if tint is not None:
                    img = img.copy()
                    wash = pygame.Surface(img.get_size())
                    wash.fill(tint)
                    img.blit(wash, (0, 0), special_flags=pygame.BLEND_MULT)
            # Invencibilidad: translúcido en vez de desaparecer
            if (spr is self.player and self.player.invincible and self.player.dash_time <= 0
                    and (pygame.time.get_ticks() // 70) % 2 == 0):
                img = img.copy()
                img.set_alpha(90)
            # Anclaje por los pies (el visual puede exceder el rect de colisión)
            dest = img.get_rect(midbottom=(spr.rect.centerx + ox, spr.rect.bottom + oy))
            # Giro del torbellino
            if spr is self.player and self.player.spin_t > 0:
                ang = (self.player.spin_t / 0.3) * 360.0
                img = pygame.transform.rotate(img, ang)
                dest = img.get_rect(center=dest.center)
            self.screen.blit(img, dest)
            # Marca de muerte: contorno rojo
            st = getattr(spr, 'status', None)
            if st is not None and spr is not self.player and st.has('mark'):
                pygame.draw.rect(self.screen, (255, 70, 70), dest, 2)
            # Élite: contorno del afijo; minijefe: contorno + nombre
            elite = getattr(spr, 'elite', None)
            if elite is not None:
                pygame.draw.rect(self.screen, elite.get('outline', (255, 220, 100)),
                                dest, 2)
            if getattr(spr, 'miniboss', None) is not None:
                r = dest
                pygame.draw.rect(self.screen, (255, 200, 60), r, 2)
                nm = self.font_small.render(spr.display_name, True, (255, 200, 60))
                self.screen.blit(nm, (r.centerx - nm.get_width() // 2, r.top - 16))
            if spr is not self.player and getattr(spr, 'posture_max', 0) > 0:
                broken = getattr(spr, 'posture_broken_t', 0) > 0
                if broken or spr.posture < spr.posture_max:
                    bar = pygame.Rect(dest.centerx - 22, dest.top - 8, 44, 4)
                    pygame.draw.rect(self.screen, (35, 35, 42), bar, border_radius=2)
                    fraction = 1.0 if broken else spr.posture / spr.posture_max
                    ratio = spr.posture / spr.posture_max
                    color = ((255, 90, 75) if broken else
                             (255, 125, 70) if ratio <= 0.3 else
                             (255, 205, 85) if ratio <= 0.65 else
                             (130, 205, 235))
                    pygame.draw.rect(self.screen, color,
                                     pygame.Rect(bar.x, bar.y, int(bar.w * fraction), bar.h),
                                     border_radius=2)
        execute_target = self.execution_target()
        if execute_target is not None:
            center = (execute_target.rect.centerx + ox,
                      execute_target.rect.centery + oy)
            reduced = self.settings.get('reduced_motion') or self.settings.get('reduced_flashes')
            pulse = 30 if reduced else 30 + int(4 * math.sin(pygame.time.get_ticks() * 0.012))
            pygame.draw.circle(self.screen, (255, 220, 95), center, pulse, 2)
            prompt = self.font.render('Z: REMATAR', True, (255, 235, 130))
            box = pygame.Rect(center[0] - prompt.get_width() // 2 - 7,
                              center[1] - pulse - 30,
                              prompt.get_width() + 14, prompt.get_height() + 4)
            pygame.draw.rect(self.screen, (20, 20, 26), box, border_radius=3)
            pygame.draw.rect(self.screen, (255, 220, 95), box, 1, border_radius=3)
            self.screen.blit(prompt, (box.x + 7, box.y + 2))
        for echo in self.death_visuals:
            draw_death_echo(self.screen, echo, off)
        # Barra de carga del ataque (guerrero)
        if self.charging > 0 and self.player is not None:
            from systems.attack_variants import CHARGE_PROFILES
            pr = self.player.rect.move((ox, oy))
            bw = 54
            bx = pr.centerx - bw // 2
            by = pr.top - 12
            pygame.draw.rect(self.screen, (40, 40, 40), (bx, by, bw, 6), border_radius=2)
            base = CHARGE_PROFILES[self.player.character_class]['color']
            col = (255, 245, 180) if self.charging >= 1.0 else base
            pygame.draw.rect(self.screen, col, (bx, by, int(bw * self.charging), 6), border_radius=2)
            variant = self.charge_variant
            if variant == 'neutral':
                variant = self.attack_variant()
            if variant != 'neutral':
                label = {'up': '↑', 'down': '↓', 'dash': '→'}[variant]
                cue = self.font_small.render(label, True, col)
                self.screen.blit(cue, (pr.centerx - cue.get_width() // 2, by - 15))
        # Proyectiles hostiles
        for proj in self.projectiles:
            if not near_view(proj.rect, view_center, SCREEN_WIDTH, SCREEN_HEIGHT, 40):
                continue
            self.screen.blit(proj.image, proj.rect.move((ox, oy)))
        # Proyectiles aliados
        for shot in self.ally_shots:
            if not near_view(shot.rect, view_center, SCREEN_WIDTH, SCREEN_HEIGHT, 40):
                continue
            if getattr(shot, 'visual', 'orb') == 'arrow':
                center = (shot.rect.centerx + ox, shot.rect.centery + oy)
                velocity = shot.velocity.normalize() if shot.velocity.length() else pygame.Vector2(1, 0)
                tail = (center[0] - int(velocity.x * 18), center[1] - int(velocity.y * 18))
                pygame.draw.line(self.screen, shot.color, tail, center, 3)
                side = pygame.Vector2(-velocity.y, velocity.x)
                pygame.draw.line(self.screen, shot.color, center,
                                 (center[0] - int(velocity.x * 6 + side.x * 4),
                                  center[1] - int(velocity.y * 6 + side.y * 4)), 2)
                pygame.draw.line(self.screen, shot.color, center,
                                 (center[0] - int(velocity.x * 6 - side.x * 4),
                                  center[1] - int(velocity.y * 6 - side.y * 4)), 2)
            elif getattr(shot, 'visual', 'orb') == 'scythe':
                center = (shot.rect.centerx + ox, shot.rect.centery + oy)
                velocity = (shot.velocity.normalize() if shot.velocity.length()
                            else pygame.Vector2(1, 0))
                angle = math.degrees(math.atan2(-velocity.y, velocity.x))
                blade = pygame.Surface((30, 30), pygame.SRCALPHA)
                pygame.draw.arc(blade, (*shot.color, 235), (3, 3, 24, 24),
                                math.radians(205), math.radians(350), 4)
                blade = pygame.transform.rotate(blade, angle)
                self.screen.blit(blade, blade.get_rect(center=center))
            else:
                self.screen.blit(shot.image, shot.rect.move((ox, oy)))
        # Meteoritos entrantes: marcador rojo pulsante
        pulse = 2 + int(2 * abs(((pygame.time.get_ticks() / 1000.0 * 6) % 2) - 1))
        for m in self.pending_meteors:
            c = (int(m['x']) + ox, int(m['y']) + oy)
            pygame.draw.circle(self.screen, (255, 60, 40), c, 120, pulse)
            pygame.draw.line(self.screen, (255, 60, 40), (c[0] - 12, c[1]), (c[0] + 12, c[1]), 2)
            pygame.draw.line(self.screen, (255, 60, 40), (c[0], c[1] - 12), (c[0], c[1] + 12), 2)
        # Ventiscas activas
        for z in self.blizzards:
            c = (int(z['x']) + ox, int(z['y']) + oy)
            surf = pygame.Surface((200, 200), pygame.SRCALPHA)
            pygame.draw.circle(surf, (150, 200, 255, 70), (100, 100), 100)
            self.screen.blit(surf, (c[0] - 100, c[1] - 100))
        # Órbita arcana
        if self.player is not None and 'arcane_orbit' in self.player.unlocked_abilities:
            for k in range(2):
                ang = self.orb_angle + k * math.pi
                oc = (int(self.player.rect.centerx + math.cos(ang) * 58) + ox,
                      int(self.player.rect.centery + math.sin(ang) * 58) + oy)
                pygame.draw.circle(self.screen, (120, 220, 255), oc, 6)
                pygame.draw.circle(self.screen, (255, 255, 255), oc, 2)
        # Telegraph de slam/salto: círculo de advertencia
        if self.boss is not None and self.boss.state in ('telegraph_slam', 'telegraph_leap'):
            c = (self.boss.rect.centerx + ox, self.boss.rect.centery + oy)
            radius = self.boss.attacks.get('slam_radius', 85)
            pygame.draw.circle(self.screen, (255, 60, 60), c, radius, 2)
            warning = self.font_small.render('IMPARABLE', True, (255, 105, 85))
            self.screen.blit(warning, (c[0] - warning.get_width() // 2,
                                       c[1] - radius - 18))
        for enemy in self.enemies:
            if isinstance(enemy, Boss):
                continue
            if not near_view(enemy.rect, view_center, SCREEN_WIDTH, SCREEN_HEIGHT, 80):
                continue
            center = (enemy.rect.centerx + ox, enemy.rect.centery + oy)
            state = getattr(enemy, 'ai_state', '')
            if state == 'telegraph':
                pygame.draw.circle(self.screen, (255, 105, 70), center,
                                   max(enemy.rect.width, enemy.rect.height), 2)
            elif state == 'block':
                side = 1 if enemy.direction > 0 else -1
                x = center[0] + side * (enemy.rect.width // 2 + 4)
                pygame.draw.line(self.screen, (175, 210, 235),
                                 (x, center[1] - 13), (x, center[1] + 13), 3)
        if self.active_secret_challenge is not None:
            remaining = max(0.0, self.active_secret_challenge['timer'])
            timer = self.font_big.render(f'PRUEBA {remaining:04.1f}s', True, (255, 210, 90))
            self.screen.blit(timer, (SCREEN_WIDTH // 2 - timer.get_width() // 2, 190))
        # Charcos de veneno
        for h in self.hazards:
            c = (int(h['x']) + ox, int(h['y']) + oy)
            alpha = max(60, int(160 * (1 - h['t'] / h['duration'])))
            surf = pygame.Surface((h['radius'] * 2, h['radius'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (60, 200, 80, alpha), (h['radius'], h['radius']), h['radius'])
            self.screen.blit(surf, (c[0] - h['radius'], c[1] - h['radius']))
        if self.active_room_encounter is not None:
            from systems.encounter_data import ENCOUNTERS
            state = self.active_room_encounter
            definition = ENCOUNTERS[state['room_id']]
            room = definition['room']
            pulse = 0.65 + 0.35 * math.sin(pygame.time.get_ticks() * 0.012)
            for tx in (room['x0'], room['x1'] + 1):
                x = int(tx * TILE_SIZE + ox)
                seal = pygame.Surface((12, SCREEN_HEIGHT), pygame.SRCALPHA)
                pygame.draw.rect(seal, (185, 105, 255, int(115 * pulse)),
                                 (3, 0, 6, SCREEN_HEIGHT))
                for y in range(20, SCREEN_HEIGHT, 42):
                    pygame.draw.circle(seal, (245, 205, 255, 220), (6, y), 4, 1)
                self.screen.blit(seal, (x - 6, 0))
            remaining = len([enemy for enemy in state['members'] if enemy.alive()])
            label = self.font_small.render(
                f"{definition['name']} · Oleada {state['wave'] + 1}/"
                f"{len(definition['waves'])} · {remaining} enemigos",
                True, (235, 190, 255))
            self.screen.blit(label, (SCREEN_WIDTH // 2 - label.get_width() // 2, 184))
        self.combat_visuals.draw(self.screen, off)
        # Partículas y textos flotantes
        self.fx.draw(self.screen, off, min_layer=1)
        restored_boss = {'caves': 'cavern_mother', 'sanctum': 'sanctum_guardian',
                         'peak': 'void_heart'}.get(zone_id)
        restored = (self.player is not None and restored_boss in
                    self.player.boss_defeated_ids)
        self.environment.draw_weather(self.screen, zone_id, quality, restored)
        self.environment.draw_lighting(
            self.screen, zone_id, self._dynamic_lights(ox, oy), quality,
            self.settings.get('high_contrast', False))
        self.texts.draw(self.screen, off, self.font_small)
        # Barra de hechizos
        self.ui.draw_spell_bar(self.player)
        if self.room_transition_t > 0:
            fade = min(1.0, self.room_transition_t / 0.32)
            veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            veil.fill((8, 10, 16))
            veil.set_alpha(int(175 * fade * fade))
            self.screen.blit(veil, (0, 0))

    def _draw_refuge(self, ox, oy):
        if self.player is None:
            return
        members = refuge_members(self.player)
        if not members:
            return
        ground_y = 47 * TILE_SIZE + oy
        # La fogata crece con la comunidad y funciona como centro visual.
        fire_x = 37 * TILE_SIZE + ox
        pygame.draw.rect(self.screen, (82, 62, 48),
                         (fire_x - 18, ground_y - 5, 36, 5))
        flame = 5 + min(5, len(members))
        pygame.draw.polygon(self.screen, (255, 105, 45),
                            ((fire_x - flame, ground_y - 5),
                             (fire_x, ground_y - 18 - flame),
                             (fire_x + flame, ground_y - 5)))
        pygame.draw.polygon(self.screen, (255, 225, 95),
                            ((fire_x - 3, ground_y - 5),
                             (fire_x, ground_y - 13),
                             (fire_x + 3, ground_y - 5)))
        positions = {'eira': 13, 'sira': 20, 'caldus': 27, 'ilyra': 33}
        for index, npc_id in enumerate(members):
            if npc_id == 'maela':
                continue
            tx = positions.get(npc_id, 10 + index * 6)
            x = tx * TILE_SIZE + ox
            color = NPCS[npc_id]['color']
            # Puesto de trabajo individual: techo, mesa y farol.
            pygame.draw.polygon(self.screen, color,
                                ((x - 28, ground_y - 56), (x, ground_y - 72),
                                 (x + 28, ground_y - 56)))
            pygame.draw.rect(self.screen, (52, 44, 48),
                             (x - 24, ground_y - 56, 48, 4))
            pygame.draw.rect(self.screen, (92, 67, 47),
                             (x - 19, ground_y - 18, 38, 5))
            pygame.draw.line(self.screen, (70, 55, 45),
                             (x - 16, ground_y - 13), (x - 16, ground_y), 3)
            pygame.draw.line(self.screen, (70, 55, 45),
                             (x + 16, ground_y - 13), (x + 16, ground_y), 3)
            pygame.draw.circle(self.screen, (255, 220, 105),
                               (x + 24, ground_y - 44), 4)
        # Estandarte central desbloqueado al reunir a toda la comunidad.
        if len(members) == len(NPCS):
            pole_x = 45 * TILE_SIZE + ox
            pygame.draw.line(self.screen, (185, 175, 155),
                             (pole_x, ground_y), (pole_x, ground_y - 88), 3)
            pygame.draw.polygon(self.screen, (105, 175, 205),
                                ((pole_x + 3, ground_y - 84),
                                 (pole_x + 36, ground_y - 73),
                                 (pole_x + 3, ground_y - 58)))

    def _draw_boss_cinematic(self):
        boss = self.boss or self.pending_boss_defeat
        if boss is None or (self.boss_intro_t <= 0 and self.boss_defeat_t <= 0):
            return
        height = 54
        pygame.draw.rect(self.screen, (4, 5, 9), (0, 0, SCREEN_WIDTH, height))
        pygame.draw.rect(self.screen, (4, 5, 9),
                         (0, SCREEN_HEIGHT - height, SCREEN_WIDTH, height))
        definition = BOSS_DEFS[boss.boss_id]
        if self.boss_intro_t > 0:
            title = self.font_title.render(boss.name.upper(), True,
                                           boss.phase_defs[1]['color'])
            subtitle = self.font.render(definition['epithet'], True, COLORS['WHITE'])
            line = self.font_small.render(definition['intro'], True, (205, 210, 225))
        else:
            title = self.font_title.render('SELLO QUEBRADO', True, COLORS['YELLOW'])
            subtitle = self.font.render(definition['restoration'], True, COLORS['WHITE'])
            line = None
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 74))
        self.screen.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 112))
        if line is not None:
            self.screen.blit(line, (SCREEN_WIDTH // 2 - line.get_width() // 2,
                                    SCREEN_HEIGHT - 36))

    def _draw_reward_altar(self, ox, oy):
        altar = self.boss_reward_altar
        if altar is None:
            return
        x, y = int(altar['x'] + ox), int(altar['y'] + oy)
        color = (105, 235, 150) if altar['claimed'] else (255, 210, 95)
        pygame.draw.polygon(self.screen, (70, 68, 82),
                            ((x - 24, y + 16), (x + 24, y + 16),
                             (x + 17, y - 4), (x - 17, y - 4)))
        pygame.draw.circle(self.screen, color, (x, y - 13), 10, 2)
        pygame.draw.circle(self.screen, color, (x, y - 13), 3)

    def _draw_restored_biome(self, ox, oy):
        if self.player is None:
            return
        restored = self.player.boss_defeated_ids
        if 'cavern_mother' in restored:
            for tx in range(64, 117, 9):
                x, y = tx * TILE_SIZE + ox, 47 * TILE_SIZE + oy
                pygame.draw.line(self.screen, (75, 190, 125), (x, y), (x, y - 10), 2)
                pygame.draw.circle(self.screen, (145, 240, 175), (x + 3, y - 10), 3)
        if 'sanctum_guardian' in restored:
            for tx in range(184, 238, 10):
                x, y = tx * TILE_SIZE + ox, 46 * TILE_SIZE + oy
                pygame.draw.circle(self.screen, (225, 180, 255), (x, y), 5, 1)
                pygame.draw.line(self.screen, (155, 105, 230), (x - 4, y), (x + 4, y), 1)
        if 'void_heart' in restored:
            for tx in range(244, 299, 11):
                x, y = tx * TILE_SIZE + ox, 47 * TILE_SIZE + oy
                pygame.draw.circle(self.screen, (185, 225, 255), (x, y - 16), 3)

    def _draw_ability_routes(self, ox, oy):
        if self.player is None:
            return
        from systems.route_data import ROUTES
        palette = {
            'double_jump': (105, 220, 255), 'wall_jump': (135, 235, 145),
            'dash': (220, 105, 245), 'teleport': (255, 175, 75),
        }
        for route_id, route in ROUTES.items():
            done = route_id in self.player.completed_routes
            unlocked = route['required'] in self.player.unlocked_abilities
            color = ((95, 215, 125) if done else
                     palette[route['required']] if unlocked else (90, 92, 105))
            for point, radius in ((route['start'], 7), (route['goal'], 10)):
                x = point[0] * TILE_SIZE + TILE_SIZE // 2 + ox
                y = (point[1] + 1) * TILE_SIZE + oy - 5
                if -20 <= x <= SCREEN_WIDTH + 20 and -20 <= y <= SCREEN_HEIGHT + 20:
                    pygame.draw.circle(self.screen, color, (x, y), radius, 2)
                    pygame.draw.circle(self.screen, color, (x, y), 2)

    def _dynamic_lights(self, ox, oy):
        lights = []
        if self.player is not None:
            class_colors = {
                'warrior': (255, 185, 95), 'rogue': (125, 210, 165),
                'mage': (145, 170, 255), 'ranger': (170, 220, 125),
                'kitsune': (255, 105, 185),
                'reaper': (80, 235, 220),
            }
            color = class_colors.get(self.player.character_class, (190, 210, 255))
            lights.append((self.player.rect.centerx + ox, self.player.rect.centery + oy,
                           72, color, 80))
        for cp in self.game_map.checkpoints:
            if self.player is not None and cp['id'] in self.player.unlocked_checkpoints:
                lights.append((cp['rect'].centerx + ox, cp['rect'].centery + oy,
                               105, (95, 220, 255), 105))
        for shot in self.ally_shots:
            lights.append((shot.rect.centerx + ox, shot.rect.centery + oy,
                           54, getattr(shot, 'color', (255, 160, 90)), 125))
        for projectile in self.projectiles:
            lights.append((projectile.rect.centerx + ox, projectile.rect.centery + oy,
                           48, (205, 80, 255), 100))
        if self.boss is not None:
            phase_color = self.boss.phase_defs.get(self.boss.phase, {}).get(
                'color', (220, 80, 255))
            lights.append((self.boss.rect.centerx + ox, self.boss.rect.centery + oy,
                           125, phase_color, 100))
        for meteor in self.pending_meteors:
            lights.append((meteor['x'] + ox, meteor['y'] + oy,
                           115, (255, 100, 55), 135))
        return lights

    def _biome_transition(self, fallback_zone):
        """Blend both sides of a zone boundary over a 12-tile corridor."""
        if self.player is None:
            return fallback_zone, None
        x = self.player.rect.centerx
        half_width = TILE_SIZE * 6
        zones = self.game_map.zones
        for index in range(len(zones) - 1):
            boundary = (zones[index]['x1'] + 1) * TILE_SIZE
            if boundary - half_width <= x <= boundary + half_width:
                progress = (x - (boundary - half_width)) / (half_width * 2)
                return zones[index]['id'], (zones[index + 1]['id'], progress)
        return fallback_zone, None

    def _entity_frame(self, spr):
        """Retorna (surface, flip_h, scale) del frame animado actual."""
        from constants import ATTACK_COOLDOWN
        t = getattr(spr, 'anim_t', 0.0)
        if spr is self.player:
            frames = self.sprite_frames.get(('player', spr.character_class),
                                            self.sprite_frames[('player', 'warrior')])
            if getattr(spr, 'hit_flash', 0) > 0 and frames.get('hurt'):
                state = 'hurt'
                img = pick_frame(frames, 'hurt', state_elapsed(spr, state, t))
            elif getattr(spr, 'action_anim_t', 0) > 0:
                state = 'attack'
                state_elapsed(spr, state, t)
                duration = max(0.01, getattr(spr, 'action_anim_duration', ATTACK_COOLDOWN))
                progress = 1.0 - min(1.0, spr.action_anim_t / duration)
                img = pick_frame(frames, 'attack', t, progress=progress, loop=False)
            elif not spr.on_ground:
                state = 'jump' if spr.velocity.y < 80 else 'fall'
                state_elapsed(spr, state, t)
                jump_frames = frames.get('fall') or frames.get('jump')
                index = 0 if spr.velocity.y < 80 else len(jump_frames) - 1
                img = jump_frames[index]
            elif abs(spr.velocity.x) > 10:
                state = 'run'
                img = pick_frame(frames, 'run', state_elapsed(spr, state, t))
            else:
                state = 'idle'
                img = pick_frame(frames, 'idle', state_elapsed(spr, state, t))
            motion_t = state_elapsed(spr, state, t)
            img = add_secondary_motion(img, state, motion_t, spr.velocity.x, spr.velocity.y,
                                       self.settings.get('reduced_motion', False))
            return img, not spr.facing_right, 1.0
        if isinstance(spr, Boss):
            frames = self.sprite_frames[('boss', spr.boss_id)]
            if getattr(spr, 'flash_t', 0) > 0 and frames.get('hurt'):
                state = 'hurt'
                img = pick_frame(frames, 'hurt', state_elapsed(spr, state, t))
            elif (spr.state.startswith('telegraph') or spr.state in ('charging', 'leaping', 'meteor_fall')):
                state = 'telegraph' if spr.state.startswith('telegraph') else 'attack'
                img = pick_frame(frames, 'attack', state_elapsed(spr, state, t))
            elif abs(spr.velocity.x) > 5:
                state = 'run'
                img = pick_frame(frames, 'run', state_elapsed(spr, state, t))
            else:
                state = 'idle'
                img = pick_frame(frames, 'idle', state_elapsed(spr, state, t))
            img = add_secondary_motion(img, state, state_elapsed(spr, state, t),
                                       spr.velocity.x, spr.velocity.y,
                                       self.settings.get('reduced_motion', False))
            if spr.phase > 1:
                img = img.copy()
                phase_color = spr.phase_defs[spr.phase]['color']
                strength = 14 if spr.phase == 2 else 28
                tint = pygame.Surface(img.get_size())
                tint.fill(tuple(channel * strength // 255 for channel in phase_color))
                img.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            return img, spr.direction < 0, 1.0
        # Enemigos (minijefes escalados por su rect)
        miniboss_id = getattr(spr, 'miniboss', None)
        frames = self.sprite_frames.get(
            ('miniboss', miniboss_id) if miniboss_id else
            ('enemy', getattr(spr, 'enemy_type', 'skeleton')),
            self.sprite_frames[('enemy', 'skeleton')])
        if getattr(spr, 'hit_flash', 0) > 0 and frames.get('hurt'):
            state = 'hurt'
            img = pick_frame(frames, 'hurt', state_elapsed(spr, state, t))
            visual_heights = {'slime': 38, 'skeleton': 52, 'bat': 40, 'goblin': 50,
                              'moss_boar': 46, 'crystal_beetle': 48,
                              'ruin_drowned': 54, 'rune_acolyte': 54,
                              'storm_harpy': 50}
            target_height = visual_heights.get(getattr(spr, 'enemy_type', ''), 48)
            scale = 1.0 if miniboss_id else target_height / max(1, img.get_height())
            img = add_secondary_motion(img, state, t,
                                       getattr(spr.velocity, 'x', 0),
                                       getattr(spr.velocity, 'y', 0),
                                       self.settings.get('reduced_motion', False))
            return img, getattr(spr, 'direction', 1) < 0, scale
        ai_state = getattr(spr, 'ai_state', '')
        if ai_state in ('telegraph', 'attack') and frames.get('attack'):
            state = 'telegraph' if ai_state == 'telegraph' else 'attack'
            img = pick_frame(frames, 'attack', state_elapsed(spr, state, t))
        elif getattr(spr, 'flying', False):
            state = 'run'
            img = pick_frame(frames, 'run', state_elapsed(spr, state, t))
        elif not getattr(spr, 'on_ground', True):
            state = 'jump' if spr.velocity.y < 80 else 'fall'
            img = pick_frame(frames, 'jump', state_elapsed(spr, state, t))
        elif abs(getattr(spr, 'velocity', pygame.math.Vector2()).x) > 5:
            state = 'run'
            img = pick_frame(frames, 'run', state_elapsed(spr, state, t))
        else:
            state = 'idle'
            img = pick_frame(frames, 'idle', state_elapsed(spr, state, t))
        img = add_secondary_motion(img, state, state_elapsed(spr, state, t),
                                   getattr(spr.velocity, 'x', 0),
                                   getattr(spr.velocity, 'y', 0),
                                   self.settings.get('reduced_motion', False))
        visual_heights = {'slime': 38, 'skeleton': 52, 'bat': 40, 'goblin': 50,
                          'moss_boar': 46, 'crystal_beetle': 48,
                          'ruin_drowned': 54, 'rune_acolyte': 54,
                          'storm_harpy': 50}
        target_height = visual_heights.get(getattr(spr, 'enemy_type', ''), 48)
        scale = 1.0 if miniboss_id else target_height / max(1, img.get_height())
        return img, getattr(spr, 'direction', 1) < 0, scale

    def _white_copy(self, image):
        if self.settings.get('reduced_flashes', False):
            return image
        img = image.copy()
        flash = img.copy()
        flash.fill((255, 255, 255))
        img.blit(flash, (0, 0), special_flags=pygame.BLEND_ADD)
        return img
