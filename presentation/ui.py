# ui.py - Dibujo de menús y HUD. Sin lógica de juego.

import pygame
from constants import COLORS, SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE
from systems.balance_data import BOSS_DEFS
from systems.skills import get_skill_categories

CATEGORY_COLORS = {
    'combat': (255, 100, 100),
    'defense': (100, 200, 255),
    'movement': (100, 255, 150),
    'utility': (255, 255, 100),
}

class UI:
    def __init__(self, screen, font, font_small, font_big, font_title, mouse_pos=None):
        self.screen = screen
        self.font = font
        self.font_small = font_small
        self.font_big = font_big
        self.font_title = font_title
        self.mouse_pos = mouse_pos or pygame.mouse.get_pos
        self.sprite_frames = {}
        self.art_assets = {}
        self.high_contrast = False

    def set_accessibility(self, high_contrast=False):
        self.high_contrast = bool(high_contrast)

    def set_art_assets(self, sprite_frames, art_assets):
        self.sprite_frames = sprite_frames
        self.art_assets = art_assets

    def _item_icon(self, item):
        if not item:
            return None
        base_id = item.get('base_id', '')
        slot = item.get('slot', '')
        for key in ('hunter_eye', 'reaper', 'staff', 'bow', 'dagger'):
            if key in base_id:
                return self.art_assets.get(key)
        return self.art_assets.get(slot)

    def _wrap_text(self, text, font, max_width):
        lines, current = [], ''
        for word in text.split():
            candidate = f'{current} {word}'.strip()
            if current and font.size(candidate)[0] > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines

    def _dark_overlay(self, alpha=220):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((8, 10, 16))
        overlay.set_alpha(alpha)
        self.screen.blit(overlay, (0, 0))

    def draw_dialogue(self, speaker, text, page, total, accent=(214, 170, 78),
                      choices=(), selected=0):
        self._dark_overlay(115)
        panel = pygame.Rect(70, SCREEN_HEIGHT - 225, SCREEN_WIDTH - 140, 175)
        pygame.draw.rect(self.screen, (20, 23, 32), panel, border_radius=6)
        pygame.draw.rect(self.screen, accent, panel, 2, border_radius=6)
        portrait = self.art_assets.get('shopkeeper')
        text_x = panel.x + 28
        if portrait is not None:
            portrait = pygame.transform.scale(portrait, (88, 112))
            portrait = portrait.copy()
            tint = pygame.Surface(portrait.get_size(), pygame.SRCALPHA)
            tint.fill((*accent, 255))
            portrait.blit(tint, (0, 0), special_flags=pygame.BLEND_MULT)
            self.screen.blit(portrait, portrait.get_rect(midbottom=(panel.x + 64, panel.bottom - 20)))
            text_x = panel.x + 125
        name = self.font_big.render(speaker, True, accent)
        self.screen.blit(name, (text_x, panel.y + 18))
        y = panel.y + 58
        for line in self._wrap_text(text, self.font, panel.right - text_x - 28):
            self.screen.blit(self.font.render(line, True, COLORS['WHITE']), (text_x, y))
            y += 25
        counter = self.font_small.render(f'{page}/{total}', True, COLORS['GRAY'])
        self.screen.blit(counter, (panel.right - counter.get_width() - 18, panel.bottom - 26))
        if choices:
            choice_x = text_x
            choice_y = panel.bottom - 55
            for index, (label, _action) in enumerate(choices):
                prefix = '> ' if index == selected else '  '
                color = COLORS['YELLOW'] if index == selected else COLORS['GRAY']
                option = self.font.render(prefix + label, True, color)
                self.screen.blit(option, (choice_x, choice_y))
                choice_x += option.get_width() + 28

    def draw_quest_journal(self, player):
        from systems.npc_data import NPCS
        from systems.quest_data import QUESTS, condition_progress, quest_status

        self._dark_overlay()
        panel = pygame.Rect(80, 42, SCREEN_WIDTH - 160, SCREEN_HEIGHT - 84)
        pygame.draw.rect(self.screen, (18, 22, 29), panel, border_radius=6)
        pygame.draw.rect(self.screen, (102, 146, 168), panel, 2, border_radius=6)
        title = self.font_title.render('DIARIO DE MISIONES', True, COLORS['YELLOW'])
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 18))
        status_labels = {
            'locked': ('BLOQUEADA', COLORS['GRAY']),
            'available': ('DISPONIBLE', (100, 205, 255)),
            'active': ('EN CURSO', COLORS['YELLOW']),
            'ready': ('LISTA PARA ENTREGAR', COLORS['GREEN']),
            'completed': ('COMPLETADA', (120, 210, 145)),
        }
        y = panel.y + 78
        for quest_id, quest in QUESTS.items():
            status = quest_status(player, quest_id)
            label, color = status_labels[status]
            row = pygame.Rect(panel.x + 24, y, panel.width - 48, 92)
            pygame.draw.rect(self.screen, (29, 34, 43), row, border_radius=4)
            pygame.draw.rect(self.screen, color, row, 1, border_radius=4)
            shown_title = quest['title'] if status != 'locked' else '???'
            self.screen.blit(self.font_big.render(shown_title, True, COLORS['WHITE']),
                             (row.x + 14, row.y + 10))
            tag = self.font_small.render(label, True, color)
            self.screen.blit(tag, (row.right - tag.get_width() - 14, row.y + 13))
            if status != 'locked':
                summary = self._wrap_text(quest['summary'], self.font_small, row.width - 28)[0]
                self.screen.blit(self.font_small.render(summary, True, COLORS['GRAY']),
                                 (row.x + 14, row.y + 42))
                current, target = condition_progress(player, quest['condition'])
                giver = NPCS[quest['giver']]['name'].split(',')[0]
                progress = self.font_small.render(
                    f'{giver} · Progreso: {current}/{target}', True, color)
                self.screen.blit(progress, (row.x + 14, row.y + 66))
                reward = quest['reward']
                reward_text = (f"Recompensa: {reward['xp']} XP · {reward['gold']} oro · "
                               f"{reward['skill_points']} puntos")
                rendered = self.font_small.render(reward_text, True, (210, 180, 100))
                self.screen.blit(rendered, (row.right - rendered.get_width() - 14, row.y + 66))
            y += 103

    # --- Menú clases ---
    def draw_class_menu(self, character_classes, save_exists=False):
        s = self.screen
        s.fill(COLORS['BLACK'])
        title = self.font_title.render("METROIDVANIA PYTHON", True, COLORS['YELLOW'])
        subtitle = self.font.render("Selecciona tu clase", True, COLORS['GRAY'])
        s.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 40))
        s.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 90))

        classes = list(character_classes.items())
        compact = len(classes) > 4
        ncols = 3 if compact else (2 if len(classes) > 3 else 3)
        card_width, card_height = (280, 175) if compact else (300, 200)
        grid_w = card_width * ncols + 20 * (ncols - 1)
        start_x = (SCREEN_WIDTH - grid_w) // 2
        y0 = 130
        mouse_pos = self.mouse_pos()
        for idx, (key, data) in enumerate(classes):
            col, row = idx % ncols, idx // ncols
            x = start_x + col * (card_width + 20)
            y = y0 + row * (card_height + 15)
            rect = pygame.Rect(x, y, card_width, card_height)
            is_hover = rect.collidepoint(mouse_pos)
            pygame.draw.rect(s, (60, 60, 80) if is_hover else (40, 40, 50), rect, border_radius=8)
            pygame.draw.rect(s, COLORS['YELLOW'] if is_hover else COLORS['GRAY'], rect, 2, border_radius=8)
            frames = self.sprite_frames.get(('player', key), {})
            portrait = frames.get('idle', [None])[0]
            if portrait is not None:
                portrait = pygame.transform.scale(portrait, (72, 84))
                s.blit(portrait, portrait.get_rect(topright=(rect.right - 12, rect.top + 12)))
            s.blit(self.font_big.render(data['name'], True, COLORS['WHITE']), (x + 15, y + 12))
            for i, stat in enumerate([f"Vida: {data['health']}", f"Velocidad: {data['speed']}", f"Daño: {data['damage']}"]):
                s.blit(self.font_small.render(stat, True, COLORS['GREEN']), (x + 15, y + 55 + i * 20))
            desc_y = y + (112 if compact else 122)
            ability_y = y + (132 if compact else 142)
            s.blit(self.font_small.render(data['description'][:36], True, COLORS['GRAY']), (x + 15, desc_y))
            s.blit(self.font_small.render(f"Habilidad: {data['starting_ability']}", True, COLORS['ORANGE']), (x + 15, ability_y))
            if is_hover:
                hover_y = y + (151 if compact else 165)
                s.blit(self.font_small.render("CLICK para seleccionar", True, COLORS['YELLOW']), (x + 15, hover_y))
        n = len(classes)
        controls = self.font.render(f"Mouse: Seleccionar  |  1-{n}: Teclado rápido", True, COLORS['GRAY'])
        s.blit(controls, (SCREEN_WIDTH // 2 - controls.get_width() // 2, SCREEN_HEIGHT - 60))
        if save_exists:
            cont = self.font.render("L: Continuar partida guardada (equipo + puertas)", True, COLORS['GREEN'])
            s.blit(cont, (SCREEN_WIDTH // 2 - cont.get_width() // 2, SCREEN_HEIGHT - 36))

    def class_card_at(self, mouse_pos):
        import math as _m
        n = 4
        try:
            from constants import CHARACTER_CLASSES
            n = len(CHARACTER_CLASSES)
        except Exception:
            pass
        compact = n > 4
        ncols = 3 if compact else (2 if n > 3 else 3)
        card_width, card_height = (280, 175) if compact else (300, 200)
        grid_w = card_width * ncols + 20 * (ncols - 1)
        start_x = (SCREEN_WIDTH - grid_w) // 2
        y0 = 130
        for idx in range(n):
            col, row = idx % ncols, idx // ncols
            x = start_x + col * (card_width + 20)
            y = y0 + row * (card_height + 15)
            if pygame.Rect(x, y, card_width, card_height).collidepoint(mouse_pos):
                return idx
        return None

    # --- HUD ---
    def draw_game_ui(self, player, zone_name="", gate_prompt="", shop_prompt=""):
        s = self.screen
        if self.high_contrast:
            pygame.draw.rect(s, (0, 0, 0), pygame.Rect(8, 8, SCREEN_WIDTH - 16, 112))
            pygame.draw.rect(s, COLORS['WHITE'], pygame.Rect(8, 8, SCREEN_WIDTH - 16, 112), 1)
            pygame.draw.rect(s, (0, 0, 0), pygame.Rect(0, SCREEN_HEIGHT - 32,
                                                     SCREEN_WIDTH, 32))
        pct = player.health / max(1, player.max_health)
        hp_color = (230, 55, 65) if pct > 0.3 else (255, 190, 45)
        pygame.draw.rect(s, (18, 20, 27), (16, 14, 262, 50), border_radius=6)
        pygame.draw.rect(s, (95, 100, 115), (16, 14, 262, 50), 1, border_radius=6)
        pygame.draw.rect(s, (40, 40, 40), (22, 22, 250, 22), border_radius=3)
        pygame.draw.rect(s, hp_color, (22, 22, int(250 * pct), 22), border_radius=3)
        pygame.draw.rect(s, COLORS['WHITE'], (22, 22, 250, 22), 1, border_radius=3)
        hp_text = self.font.render(f"{player.health}/{player.max_health}", True, COLORS['WHITE'])
        s.blit(hp_text, (147 - hp_text.get_width() // 2, 22))

        xp_pct = player.experience / max(1, player.xp_to_next_level)
        pygame.draw.rect(s, (40, 40, 60), (22, 50, 250, 7), border_radius=2)
        pygame.draw.rect(s, (100, 150, 255), (22, 50, int(250 * xp_pct), 7), border_radius=2)

        info_y = 65
        for t in [
            f"Nivel {player.level}  |  XP: {player.experience}/{player.xp_to_next_level}  |  Oro: {getattr(player, 'gold', 0)}",
            f"Clase: {player.name}  |  Pts: {player.skill_points}  |  Inv: {len(getattr(player, 'inventory', []))}",
            f"Dano: {player.damage}  |  Vel: {player.speed:.0f} px/s  |  Crit: {player._stat_multipliers.get('crit_chance', 0)*100:.0f}%",
        ]:
            s.blit(self.font_small.render(t, True, COLORS['WHITE']), (20, info_y))
            info_y += 20
        if player.unlocked_abilities:
            abilities = sorted(player.unlocked_abilities)
            summary = ", ".join(abilities[:3])
            if len(abilities) > 3:
                summary += f" +{len(abilities) - 3}"
            s.blit(self.font_small.render("Habilidades: " + summary, True,
                                          COLORS['ORANGE']), (20, info_y + 5))
        if getattr(player, 'combo_timer', 0) > 0:
            mode = 'AÉREO' if getattr(player, 'combo_mode', '') == 'air' else 'TIERRA'
            combo = self.font.render(
                f'{mode} · COMBO {getattr(player, "combo_step", 0) + 1}',
                True, (255, 220, 100))
            s.blit(combo, (SCREEN_WIDTH // 2 - combo.get_width() // 2, 92))
            chain = min(5, getattr(player, 'combo_step', 0) + 1)
            for index in range(5):
                color = (255, 215, 80) if index < chain else (65, 65, 75)
                pygame.draw.rect(s, color,
                                 pygame.Rect(SCREEN_WIDTH // 2 - 43 + index * 18, 116, 14, 4),
                                 border_radius=2)
        # Estados activos del jugador (veneno, chill...)
        yst = info_y + 24
        for name, secs, color in player.status.summary():
            chip = self.font_small.render(f"{name} {secs:.1f}s", True, color)
            s.blit(chip, (20, yst))
            yst += 16
        bosses = len(getattr(player, 'boss_defeated_ids', set()))
        cyc = getattr(player, 'ng_plus', 0)
        s.blit(self.font_small.render(f"Jefes: {bosses}/3  |  Ciclo: NG+{cyc}", True, COLORS['YELLOW']), (280, 65))
        if bosses >= 3:
            ng = self.font.render(f"P: Nuevo Juego+ (ciclo {cyc + 1}, enemigos más duros y mejor botín)", True, COLORS['GREEN'])
            s.blit(ng, (SCREEN_WIDTH // 2 - ng.get_width() // 2, 110))
        pots = self.font.render(f"Pociones: {getattr(player, 'potions', 0)} (Q)", True, COLORS['GREEN'])
        s.blit(pots, (SCREEN_WIDTH - pots.get_width() - 20, 44))
        parry_key = '?'
        from systems import controls as _controls
        if _controls.codes('parry'):
            parry_key = _controls.key_label(_controls.codes('parry')[0])
        if player.parry_window > 0:
            parry_label, parry_color = 'PARADA', (150, 235, 255)
        elif player.parry_cooldown > 0:
            parry_label, parry_color = f'{player.parry_cooldown:.1f}s', COLORS['GRAY']
        else:
            parry_label, parry_color = 'LISTA', (130, 235, 155)
        parry = self.font_small.render(f'{parry_key}: Parada · {parry_label}', True, parry_color)
        s.blit(parry, (SCREEN_WIDTH - parry.get_width() - 20, 66))
        if player.character_class == 'reaper':
            souls = getattr(player, 'souls', 0)
            limit = player.soul_limit()
            width = 180
            x, y = SCREEN_WIDTH - width - 20, 88
            pygame.draw.rect(s, (20, 35, 42), (x, y, width, 13), border_radius=3)
            pygame.draw.rect(s, (65, 220, 205),
                             (x, y, int(width * souls / max(1, limit)), 13),
                             border_radius=3)
            pygame.draw.rect(s, (145, 245, 235), (x, y, width, 13), 1,
                             border_radius=3)
            soul_text = self.font_small.render(
                f'ALMAS {souls}/{limit} · RMB: Cosecha (30)', True, COLORS['WHITE'])
            s.blit(soul_text, (x + width - soul_text.get_width(), y + 15))
        if zone_name:
            z = self.font.render(zone_name, True, COLORS['YELLOW'])
            s.blit(z, (SCREEN_WIDTH - z.get_width() - 20, 20))
        if gate_prompt:
            g = self.font_small.render(gate_prompt, True, COLORS['ORANGE'])
            s.blit(g, (SCREEN_WIDTH // 2 - g.get_width() // 2, 44))
        if shop_prompt:
            sp = self.font.render(shop_prompt, True, COLORS['YELLOW'])
            s.blit(sp, (SCREEN_WIDTH // 2 - sp.get_width() // 2, 66))
        self.draw_spell_bar(player)
        controls = self._controls_line()
        s.blit(controls, (SCREEN_WIDTH // 2 - controls.get_width() // 2, SCREEN_HEIGHT - 25))

    def _controls_line(self):
        from systems import controls as _c
        parts = [('attack', 'Atacar'), ('dash', 'Dash'), ('parry', 'Parada'),
                 ('potion', 'Poción'), ('skills', 'Habilidades'), ('inventory', 'Equipo'),
                 ('map', 'Mapa')]
        txt = " ".join(f"{_c.key_label(_c.codes(a)[0]) if _c.codes(a) else '?'}:{short}"
                       for a, short in parts)
        return self.font_small.render(txt, True, (190, 198, 210))

    # --- Skill tree ---
    def draw_skill_tree(self, player):
        s = self.screen
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(220)
        s.blit(overlay, (0, 0))
        panel = pygame.Rect(40, 30, SCREEN_WIDTH - 80, SCREEN_HEIGHT - 60)
        pygame.draw.rect(s, (20, 20, 30), panel, border_radius=10)
        pygame.draw.rect(s, COLORS['GRAY'], panel, 2, border_radius=10)

        title = self.font_title.render(f"ARBOL DE HABILIDADES - {player.name.upper()}", True, COLORS['YELLOW'])
        s.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 45))
        s.blit(self.font_big.render(f"Puntos: {player.skill_points}", True, COLORS['GREEN']), (60, 50))
        prog = player.get_skill_tree_progress()
        s.blit(self.font.render(f"Desbloqueadas: {prog['unlocked']}/{prog['total']}  |  Gastados: {prog['points_spent']}", True, COLORS['GRAY']), (60, 90))

        categories = get_skill_categories()
        mouse_pos = self.mouse_pos()
        for i, cat in enumerate(categories):
            tx = 60 + i * 150
            tab = pygame.Rect(tx, 125, 140, 35)
            active = cat == player.skill_tree_selected_category
            bg = CATEGORY_COLORS.get(cat, COLORS['WHITE']) if active else ((80, 80, 100) if tab.collidepoint(mouse_pos) else (50, 50, 60))
            fg = COLORS['BLACK'] if active else (COLORS['WHITE'] if tab.collidepoint(mouse_pos) else COLORS['GRAY'])
            pygame.draw.rect(s, bg, tab, border_radius=5)
            pygame.draw.rect(s, COLORS['GRAY'], tab, 1, border_radius=5)
            ct = self.font.render(cat.capitalize(), True, fg)
            s.blit(ct, (tx + 70 - ct.get_width() // 2, 132))

        skills = player.get_skills_by_category(player.skill_tree_selected_category)
        for idx, (skill_id, skill) in enumerate(list(skills.items())[:5]):
            y = 180 + idx * 105
            rank, max_rank = player.skill_ranks.get(skill_id, 0), skill['max_rank']
            can_buy, _ = player.can_buy_skill(skill_id)
            item = pygame.Rect(60, y, SCREEN_WIDTH - 120, 95)
            bgc = (30, 60, 30) if rank >= max_rank else ((50, 50, 70) if can_buy else (35, 35, 45))
            bdc = COLORS['GREEN'] if rank >= max_rank else (COLORS['YELLOW'] if can_buy else (80, 80, 80))
            pygame.draw.rect(s, bgc, item, border_radius=8)
            pygame.draw.rect(s, bdc, item, 2, border_radius=8)
            s.blit(self.font_big.render(skill['icon'], True, COLORS['WHITE']), (75, y + 10))
            s.blit(self.font_big.render(f"{skill['name']}  [{rank}/{max_rank}]", True, COLORS['GREEN'] if rank >= max_rank else COLORS['WHITE']), (120, y + 10))
            s.blit(self.font.render(f"Coste: {skill['cost']} pt(s)", True, COLORS['YELLOW'] if can_buy else COLORS['GRAY']), (120, y + 50))
            s.blit(self.font_small.render(skill['description'], True, COLORS['GRAY']), (120, y + 70))
            if skill['requires'] and rank == 0:
                reqs = [player.available_skills[r]['name'] for r in skill['requires'] if r in player.available_skills]
                if reqs:
                    s.blit(self.font_small.render(f"Requiere: {', '.join(reqs)} (max)", True, COLORS['ORANGE']), (360, y + 10))
            if rank < max_rank:
                btn = pygame.Rect(60 + SCREEN_WIDTH - 200, y + 20, 120, 40)
                hover = btn.collidepoint(mouse_pos)
                pygame.draw.rect(s, CATEGORY_COLORS.get(skill['category'], COLORS['WHITE']) if can_buy and hover else (70, 70, 90), btn, border_radius=5)
                bt = self.font.render("MEJORAR" if rank > 0 else "COMPRAR", True, COLORS['WHITE'] if can_buy else COLORS['GRAY'])
                s.blit(bt, (btn.centerx - bt.get_width() // 2, btn.centery - bt.get_height() // 2))

        help_t = self.font.render("K/TAB: Cerrar  |  Click pestanas: cambiar  |  Click boton: comprar  |  R: Reset", True, COLORS['GRAY'])
        s.blit(help_t, (SCREEN_WIDTH // 2 - help_t.get_width() // 2, SCREEN_HEIGHT - 40))

    def skill_button_at(self, player, mouse_pos):
        skills = player.get_skills_by_category(player.skill_tree_selected_category)
        for idx, (skill_id, skill) in enumerate(list(skills.items())[:5]):
            y = 180 + idx * 105
            if player.skill_ranks.get(skill_id, 0) >= skill['max_rank']:
                continue
            if pygame.Rect(60 + SCREEN_WIDTH - 200, y + 20, 120, 40).collidepoint(mouse_pos):
                return skill_id
        return None

    def skill_tab_at(self, mouse_pos):
        for i, cat in enumerate(get_skill_categories()):
            if pygame.Rect(60 + i * 150, 125, 140, 35).collidepoint(mouse_pos):
                return cat
        return None

    def draw_boss_bar(self, boss):
        s = self.screen
        bw, bh = 420, 20
        bx, by = SCREEN_WIDTH // 2 - bw // 2, 10
        frac = max(0.0, boss.health / max(1, boss.max_health))
        pygame.draw.rect(s, (18, 8, 13), (bx - 6, by - 5, bw + 12, 49), border_radius=5)
        pygame.draw.rect(s, (120, 75, 85), (bx - 6, by - 5, bw + 12, 49), 1, border_radius=5)
        pygame.draw.rect(s, (30, 10, 15), (bx, by, bw, bh), border_radius=3)
        phase_colors = {1: (205, 48, 58), 2: (225, 100, 42), 3: (190, 65, 220)}
        pygame.draw.rect(s, phase_colors.get(boss.phase, (200, 30, 50)),
                         (bx, by, int(bw * frac), bh), border_radius=3)
        pygame.draw.rect(s, COLORS['WHITE'], (bx, by, bw, bh), 1, border_radius=4)
        # Pips de fase
        for i, (thr, _) in enumerate([(0.7, 1), (0.4, 2)]):
            px = bx + int(bw * thr)
            pygame.draw.line(s, COLORS['BLACK'], (px, by), (px, by + bh), 2)
        definition = BOSS_DEFS.get(getattr(boss, 'boss_id', ''), {})
        epithet = definition.get('epithet', '')
        label = self.font_small.render(
            f"{boss.name.upper()} · {epithet} · FASE {boss.phase} · {boss.health}/{boss.max_health}",
            True, COLORS['WHITE'])
        s.blit(label, (SCREEN_WIDTH // 2 - label.get_width() // 2, by + bh + 3))

    def draw_travel_menu(self, player, checkpoints):
        s = self.screen
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(220)
        s.blit(overlay, (0, 0))
        panel = pygame.Rect(180, 90, SCREEN_WIDTH - 360, SCREEN_HEIGHT - 220)
        pygame.draw.rect(s, (20, 20, 30), panel, border_radius=10)
        pygame.draw.rect(s, COLORS['GRAY'], panel, 2, border_radius=10)
        title = self.font_title.render("VIAJE RÁPIDO", True, COLORS['YELLOW'])
        s.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 105))
        mouse_pos = self.mouse_pos()
        y = 165
        for cp in checkpoints:
            unlocked = cp['id'] in player.unlocked_checkpoints
            is_respawn = player.respawn_point and abs(player.respawn_point[0] - (cp['rect'].x - 24)) < 4
            rect = pygame.Rect(210, y, SCREEN_WIDTH - 420, 56)
            bg = (45, 60, 70) if unlocked else (35, 35, 45)
            if unlocked and rect.collidepoint(mouse_pos):
                bg = (60, 80, 95)
            pygame.draw.rect(s, bg, rect, border_radius=6)
            pygame.draw.rect(s, (100, 220, 255) if unlocked else (80, 80, 80), rect, 2, border_radius=6)
            dot = (100, 220, 255) if unlocked else (90, 90, 100)
            pygame.draw.circle(s, dot, (230, y + 28), 8)
            name = cp['name'] + ("  [base]" if is_respawn else "") if unlocked else "??? (no descubierto)"
            s.blit(self.font_big.render(name, True, COLORS['WHITE'] if unlocked else (110, 110, 110)), (250, y + 12))
            y += 66
        help_t = self.font.render("Click: viajar (cura total)  |  M/ESC: cerrar", True, COLORS['GRAY'])
        s.blit(help_t, (SCREEN_WIDTH // 2 - help_t.get_width() // 2, SCREEN_HEIGHT - 110))

    def travel_item_at(self, player, checkpoints, mouse_pos):
        y = 165
        for cp in checkpoints:
            if cp['id'] in player.unlocked_checkpoints:
                if pygame.Rect(210, y, SCREEN_WIDTH - 420, 56).collidepoint(mouse_pos):
                    return cp['id']
            y += 66
        return None

    # --- Tienda ---
    # Geometría compartida draw / clicks: stock izq (1 col x6), botones + venta der.
    SHOP_STOCK_X, SHOP_STOCK_W = 80, 370
    SHOP_STOCK_Y0, SHOP_STOCK_H, SHOP_STOCK_GAP = 130, 62, 6
    SHOP_SELL_X, SHOP_SELL_W = 510, 370
    SHOP_SELL_Y0, SHOP_SELL_H, SHOP_SELL_GAP = 186, 56, 6
    SHOP_POTION_RECT = (510, 132, 180, 44)
    SHOP_REFRESH_RECT = (700, 132, 180, 44)
    SHOP_TABS = [('buy', 'Comprar'), ('upgrade', 'Mejorar'), ('craft', 'Forjar')]
    SHOP_TAB_Y, SHOP_TAB_W, SHOP_TAB_H = 78, 150, 30
    SHOP_UP_X, SHOP_UP_W = 80, 800
    SHOP_UP_Y0, SHOP_UP_H, SHOP_UP_GAP, SHOP_UP_N = 125, 54, 6, 7

    @staticmethod
    def _upgrade_entries(player):
        from systems.items import SLOTS
        entries = [player.equipment[s] for s in SLOTS if player.equipment.get(s)]
        entries.extend(player.inventory)
        return entries

    @staticmethod
    def _craft_groups(player):
        from systems.items import RARITY_ORDER, SLOT_NAMES
        groups = {}
        for it in player.inventory:
            key = (it.get('slot'), it.get('rarity'))
            groups[key] = groups.get(key, 0) + 1
        order = {r: i for i, r in enumerate(RARITY_ORDER)}
        return sorted(groups.items(),
                      key=lambda kv: (order.get(kv[0][1], 9), kv[0][0]))

    def draw_shop(self, player, stock, tab='buy'):
        from systems.items import (format_stats, buy_price, sell_price, refresh_price,
                           POTION_PRICE, POTION_MAX, upgrade_cost, upgrade_level,
                           MAX_UPGRADE, craft_result_rarity, RARITIES, SLOT_NAMES)
        s = self.screen
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(220)
        s.blit(overlay, (0, 0))
        panel = pygame.Rect(40, 30, SCREEN_WIDTH - 80, SCREEN_HEIGHT - 60)
        pygame.draw.rect(s, (20, 20, 30), panel, border_radius=10)
        pygame.draw.rect(s, COLORS['GRAY'], panel, 2, border_radius=10)
        title = self.font_title.render("HERRERÍA", True, COLORS['YELLOW'])
        s.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 36))
        gold = self.font_big.render(f"Oro: {player.gold}g", True, COLORS['YELLOW'])
        s.blit(gold, (SCREEN_WIDTH - gold.get_width() - 70, 42))
        mouse_pos = self.mouse_pos()
        # Pestañas
        tx0 = SCREEN_WIDTH // 2 - (len(self.SHOP_TABS) * (self.SHOP_TAB_W + 10)) // 2
        for i, (tid, tlabel) in enumerate(self.SHOP_TABS):
            r = pygame.Rect(tx0 + i * (self.SHOP_TAB_W + 10), self.SHOP_TAB_Y,
                            self.SHOP_TAB_W, self.SHOP_TAB_H)
            active = (tab == tid)
            bg = COLORS['YELLOW'] if active else ((70, 70, 95) if r.collidepoint(mouse_pos) else (45, 45, 60))
            pygame.draw.rect(s, bg, r, border_radius=5)
            t = self.font.render(tlabel, True, COLORS['BLACK'] if active else COLORS['WHITE'])
            s.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
        if tab == 'buy':
            self._draw_shop_buy(player, stock, mouse_pos)
        elif tab == 'upgrade':
            self._draw_shop_upgrade(player, mouse_pos)
        elif tab == 'craft':
            self._draw_shop_craft(player, mouse_pos)
        hint = self.font_small.render("Q: beber poción (+40% vida)  |  F/ESC: cerrar", True, COLORS['GRAY'])
        s.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 42))

    def _draw_shop_buy(self, player, stock, mouse_pos):
        from systems.items import format_stats, buy_price, sell_price, refresh_price, POTION_PRICE, POTION_MAX
        s = self.screen
        s.blit(self.font.render("Mercancía (click: comprar):", True, COLORS['WHITE']), (self.SHOP_STOCK_X, 108))
        for idx, it in enumerate(stock[:6]):
            y = self.SHOP_STOCK_Y0 + idx * (self.SHOP_STOCK_H + self.SHOP_STOCK_GAP)
            rect = pygame.Rect(self.SHOP_STOCK_X, y, self.SHOP_STOCK_W, self.SHOP_STOCK_H)
            price = buy_price(it)
            afford = player.gold >= price
            bg = (50, 55, 70) if afford and rect.collidepoint(mouse_pos) else (40, 40, 55)
            pygame.draw.rect(s, bg, rect, border_radius=6)
            pygame.draw.rect(s, self._rarity_color(it['rarity']), rect, 2, border_radius=6)
            s.blit(self.font.render(f"{it['name'][:30]} Nv{it.get('level',1)}", True, self._rarity_color(it['rarity'])), (rect.x + 10, y + 5))
            s.blit(self.font.render(f"{price}g", True, COLORS['YELLOW'] if afford else (150, 80, 80)), (rect.right - 70, y + 5))
            s.blit(self.font_small.render(format_stats(it.get('stats', {}))[:58], True, COLORS['GREEN']), (rect.x + 10, y + 32))
        for label, brect in [
            (f"Poción ({player.potions}/{POTION_MAX}) {POTION_PRICE}g", self.SHOP_POTION_RECT),
            (f"Surtido {refresh_price(player.level)}g", self.SHOP_REFRESH_RECT),
        ]:
            r = pygame.Rect(*brect)
            hover = r.collidepoint(mouse_pos)
            pygame.draw.rect(s, (70, 70, 95) if hover else (50, 50, 70), r, border_radius=5)
            pygame.draw.rect(s, COLORS['YELLOW'], r, 1, border_radius=5)
            t = self.font_small.render(label, True, COLORS['WHITE'])
            s.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
        s.blit(self.font.render("Tu mochila (click: vender):", True, COLORS['WHITE']), (self.SHOP_SELL_X, 164))
        for idx, it in enumerate(player.inventory[:6]):
            y = self.SHOP_SELL_Y0 + idx * (self.SHOP_SELL_H + self.SHOP_SELL_GAP)
            rect = pygame.Rect(self.SHOP_SELL_X, y, self.SHOP_SELL_W, self.SHOP_SELL_H)
            bg = (55, 55, 75) if rect.collidepoint(mouse_pos) else (40, 40, 55)
            pygame.draw.rect(s, bg, rect, border_radius=6)
            pygame.draw.rect(s, self._rarity_color(it['rarity']), rect, 1, border_radius=6)
            s.blit(self.font_small.render(f"{it['name'][:32]}", True, self._rarity_color(it['rarity'])), (rect.x + 10, y + 4))
            s.blit(self.font_small.render(f"Vende: {sell_price(it)}g", True, COLORS['YELLOW']), (rect.x + 10, y + 28))
        if len(player.inventory) > 6:
            s.blit(self.font_small.render(f"... y {len(player.inventory)-6} más (ciérrala con I para ver)", True, COLORS['GRAY']), (self.SHOP_SELL_X, 186 + 6 * 62))
        hint = self.font_small.render("Q: beber poción (+40% vida)  |  F/ESC: cerrar", True, COLORS['GRAY'])
        s.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 42))

    def _draw_shop_upgrade(self, player, mouse_pos):
        from systems.items import format_stats, upgrade_cost, upgrade_level, MAX_UPGRADE
        s = self.screen
        s.blit(self.font.render("Equipo + mochila (click: mejorar +12%):", True, COLORS['WHITE']),
               (self.SHOP_UP_X, 108))
        for idx, it in enumerate(self._upgrade_entries(player)[:self.SHOP_UP_N]):
            y = self.SHOP_UP_Y0 + idx * (self.SHOP_UP_H + self.SHOP_UP_GAP)
            rect = pygame.Rect(self.SHOP_UP_X, y, self.SHOP_UP_W, self.SHOP_UP_H)
            up = upgrade_level(it)
            maxed = up >= MAX_UPGRADE
            cost = upgrade_cost(it)
            afford = player.gold >= cost and not maxed
            bg = (50, 55, 70) if afford and rect.collidepoint(mouse_pos) else (40, 40, 55)
            pygame.draw.rect(s, bg, rect, border_radius=6)
            pygame.draw.rect(s, self._rarity_color(it['rarity']), rect, 2, border_radius=6)
            s.blit(self.font.render(f"{it['name'][:34]}", True, self._rarity_color(it['rarity'])), (rect.x + 12, y + 4))
            s.blit(self.font_small.render(format_stats(it.get('stats', {}))[:70], True, COLORS['GREEN']), (rect.x + 12, y + 28))
            btn = "MÁX" if maxed else f"+{up + 1}  {cost}g"
            bt = self.font.render(btn, True, COLORS['GRAY'] if maxed or not afford else COLORS['YELLOW'])
            s.blit(bt, (rect.right - bt.get_width() - 14, y + 14))

    def _draw_shop_craft(self, player, mouse_pos):
        from systems.items import craft_result_rarity, RARITIES, SLOT_NAMES
        s = self.screen
        s.blit(self.font.render("Funde 3 piezas iguales en 1 de rareza superior:", True, COLORS['WHITE']),
               (self.SHOP_UP_X, 108))
        for idx, ((slot, rarity), count) in enumerate(self._craft_groups(player)[:self.SHOP_UP_N]):
            y = self.SHOP_UP_Y0 + idx * (self.SHOP_UP_H + self.SHOP_UP_GAP)
            rect = pygame.Rect(self.SHOP_UP_X, y, self.SHOP_UP_W, self.SHOP_UP_H)
            nxt = craft_result_rarity(rarity)
            can = nxt is not None and count >= 3
            bg = (50, 55, 70) if can and rect.collidepoint(mouse_pos) else (40, 40, 55)
            pygame.draw.rect(s, bg, rect, border_radius=6)
            pygame.draw.rect(s, self._rarity_color(rarity), rect, 2, border_radius=6)
            left = f"{count}x {SLOT_NAMES.get(slot, slot)} {RARITIES[rarity]['name']}"
            s.blit(self.font.render(left, True, self._rarity_color(rarity)), (rect.x + 12, y + 14))
            right = "MÁX" if nxt is None else (f"→ {RARITIES[nxt]['name']}  [Forjar]" if can else f"→ {RARITIES[nxt]['name']} ({count}/3)")
            bt = self.font.render(right, True, COLORS['YELLOW'] if can else COLORS['GRAY'])
            s.blit(bt, (rect.right - bt.get_width() - 14, y + 14))

    def shop_action_at(self, player, stock, mouse_pos, tab='buy'):
        tx0 = SCREEN_WIDTH // 2 - (len(self.SHOP_TABS) * (self.SHOP_TAB_W + 10)) // 2
        for i, (tid, _) in enumerate(self.SHOP_TABS):
            r = pygame.Rect(tx0 + i * (self.SHOP_TAB_W + 10), self.SHOP_TAB_Y,
                            self.SHOP_TAB_W, self.SHOP_TAB_H)
            if r.collidepoint(mouse_pos):
                return ('tab', tid)
        if tab == 'upgrade':
            for idx, it in enumerate(self._upgrade_entries(player)[:self.SHOP_UP_N]):
                y = self.SHOP_UP_Y0 + idx * (self.SHOP_UP_H + self.SHOP_UP_GAP)
                if pygame.Rect(self.SHOP_UP_X, y, self.SHOP_UP_W, self.SHOP_UP_H).collidepoint(mouse_pos):
                    return ('upgrade', it.get('id'))
            return None
        if tab == 'craft':
            for idx, ((slot, rarity), count) in enumerate(self._craft_groups(player)[:self.SHOP_UP_N]):
                y = self.SHOP_UP_Y0 + idx * (self.SHOP_UP_H + self.SHOP_UP_GAP)
                if pygame.Rect(self.SHOP_UP_X, y, self.SHOP_UP_W, self.SHOP_UP_H).collidepoint(mouse_pos):
                    return ('craft', (slot, rarity))
            return None
        for idx, it in enumerate(stock[:6]):
            y = self.SHOP_STOCK_Y0 + idx * (self.SHOP_STOCK_H + self.SHOP_STOCK_GAP)
            if pygame.Rect(self.SHOP_STOCK_X, y, self.SHOP_STOCK_W, self.SHOP_STOCK_H).collidepoint(mouse_pos):
                return ('buy', it.get('id'))
        if pygame.Rect(*self.SHOP_POTION_RECT).collidepoint(mouse_pos):
            return ('potion', None)
        if pygame.Rect(*self.SHOP_REFRESH_RECT).collidepoint(mouse_pos):
            return ('refresh', None)
        for idx, it in enumerate(player.inventory[:6]):
            y = self.SHOP_SELL_Y0 + idx * (self.SHOP_SELL_H + self.SHOP_SELL_GAP)
            if pygame.Rect(self.SHOP_SELL_X, y, self.SHOP_SELL_W, self.SHOP_SELL_H).collidepoint(mouse_pos):
                return ('sell', it.get('id'))
        return None

    def draw_spell_bar(self, player):
        from systems.spells import SPELL_DEFS, ABILITY_SPELL
        from systems import controls as _c

        inv = {v: k for k, v in ABILITY_SPELL.items()}
        class_actions = {
            'warrior': 'Ataque / Carga',
            'rogue': 'Combo',
            'ranger': 'Disparo',
            'mage': 'Proyectil arcano',
            'kitsune': 'Fuego zorro',
            'reaper': 'Danza de la Guadaña',
        }
        attack_codes = _c.codes('attack')
        attack_key = _c.key_label(attack_codes[0]) if attack_codes else '?'
        up_codes = _c.codes('jump')
        down_codes = _c.codes('down')
        up_key = _c.key_label(up_codes[0]) if up_codes else '↑'
        down_key = _c.key_label(down_codes[0]) if down_codes else '↓'
        entries = [(f"{attack_key}: {class_actions.get(player.character_class, 'Ataque')}",
                    (235, 235, 240)),
                   (f"Mantén {attack_key}: Carga · {up_key}/{down_key}: Variante",
                    (190, 205, 220))]

        for spell, meta in SPELL_DEFS.items():
            if inv.get(spell) not in player.unlocked_abilities:
                continue
            cd = player.spell_cd.get(spell, 0)
            if meta.get('passive'):
                entries.append((f"PASIVA: {meta['label']}", (170, 185, 205)))
                continue
            if meta.get('action'):
                codes = _c.codes(meta['action'])
                key = _c.key_label(codes[0]) if codes else '?'
            else:
                key = meta.get('key', '?')
            state = f"{cd:.1f}s" if cd > 0 else "LISTA"
            color = (130, 135, 145) if cd > 0 else (150, 220, 255)
            entries.append((f"{key}: {meta['label']}  {state}", color))

        x, y = 16, SCREEN_HEIGHT - 55
        for label, color in entries:
            text = self.font_small.render(label, True, color)
            width = text.get_width() + 12
            if x + width > SCREEN_WIDTH - 16:
                x = 16
                y -= 24
            rect = pygame.Rect(x, y, width, 20)
            pygame.draw.rect(self.screen, (18, 22, 30), rect, border_radius=4)
            pygame.draw.rect(self.screen, (70, 82, 98), rect, 1, border_radius=4)
            self.screen.blit(text, (x + 6, y + 2))
            x += width + 6

    # --- Pausa / controles ---
    PAUSE_BTNS = [('resume', 'Continuar'), ('save', 'Guardar partida'),
                  ('achievements', 'Logros y desafíos'),
                  ('settings', 'Configuración'),
                  ('classes', 'Abandonar a clases'), ('quit', 'Salir del juego')]
    PAUSE_BTN_X, PAUSE_BTN_W, PAUSE_BTN_Y0, PAUSE_BTN_H, PAUSE_BTN_GAP = 75, 300, 115, 38, 10
    def draw_pause(self, player=None):
        s = self.screen
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(200)
        s.blit(overlay, (0, 0))
        panel = pygame.Rect(40, 35, SCREEN_WIDTH - 80, SCREEN_HEIGHT - 70)
        pygame.draw.rect(s, (20, 20, 30), panel, border_radius=10)
        pygame.draw.rect(s, COLORS['GRAY'], panel, 2, border_radius=10)
        title = self.font_title.render("PAUSA", True, COLORS['YELLOW'])
        s.blit(title, (70, 55))
        mouse_pos = self.mouse_pos()
        for i, (bid, label) in enumerate(self.PAUSE_BTNS):
            y = self.PAUSE_BTN_Y0 + i * (self.PAUSE_BTN_H + self.PAUSE_BTN_GAP)
            rect = pygame.Rect(self.PAUSE_BTN_X, y, self.PAUSE_BTN_W, self.PAUSE_BTN_H)
            hover = rect.collidepoint(mouse_pos)
            pygame.draw.rect(s, (70, 70, 95) if hover else (45, 45, 60), rect, border_radius=5)
            pygame.draw.rect(s, COLORS['YELLOW'] if hover else COLORS['GRAY'], rect, 1, border_radius=5)
            t = self.font.render(label, True, COLORS['WHITE'])
            s.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))
        if player is not None:
            from systems.run_stats import format_play_time
            stats = player.statistics
            sx, sy = 430, 78
            heading = self.font_big.render('ESTADÍSTICAS DE PARTIDA', True, COLORS['YELLOW'])
            s.blit(heading, (sx, sy))
            hits_per_attack = stats['hits'] / max(1, stats['attacks'])
            rows = [
                ('Tiempo jugado', format_play_time(stats['play_time'])),
                ('Daño infligido', f"{stats['damage_dealt']:,}"),
                ('Daño recibido', f"{stats['damage_taken']:,}"),
                ('Ataques / impactos',
                 f"{stats['attacks']} / {stats['hits']} (x{hits_per_attack:.1f})"),
                ('Paradas / rupturas / remates',
                 f"{stats['perfect_parries']} / {stats['posture_breaks']} / {stats['executions']}"),
                ('Enemigos derrotados', str(stats['enemies_defeated'])),
                ('Jefes derrotados', str(stats['bosses_defeated'])),
                ('Mejor combo', f"x{stats['highest_combo']}"),
                ('Oro / XP obtenidos', f"{stats['gold_earned']:,} / {stats['xp_earned']:,}"),
                ('Pociones / muertes', f"{stats['potions_used']} / {stats['deaths']}"),
                ('Exploración', f"{len(player.explored_rooms)} salas · {len(player.discovered_secrets)} secretos"),
            ]
            for index, (label, value) in enumerate(rows):
                y = sy + 52 + index * 36
                pygame.draw.line(s, (55, 57, 70), (sx, y + 27), (875, y + 27), 1)
                s.blit(self.font_small.render(label, True, COLORS['GRAY']), (sx, y))
                value_text = self.font.render(value, True, COLORS['WHITE'])
                s.blit(value_text, (875 - value_text.get_width(), y - 2))
        hint = self.font_small.render("ESC: continuar", True, COLORS['GRAY'])
        s.blit(hint, (75, 575))

    def pause_action_at(self, pos):
        for i, (bid, _) in enumerate(self.PAUSE_BTNS):
            y = self.PAUSE_BTN_Y0 + i * (self.PAUSE_BTN_H + self.PAUSE_BTN_GAP)
            if pygame.Rect(self.PAUSE_BTN_X, y, self.PAUSE_BTN_W, self.PAUSE_BTN_H).collidepoint(pos):
                return (bid, None)
        return None

    def draw_achievements(self, player):
        from systems.achievements import ACHIEVEMENTS, progress
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(225)
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(35, 28, SCREEN_WIDTH - 70, SCREEN_HEIGHT - 56)
        pygame.draw.rect(self.screen, (18, 20, 28), panel, border_radius=8)
        pygame.draw.rect(self.screen, COLORS['GRAY'], panel, 2, border_radius=8)
        title = self.font_title.render('LOGROS Y DESAFÍOS', True, COLORS['YELLOW'])
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 42))
        unlocked = player.unlocked_achievements
        summary = self.font.render(f'Completados: {len(unlocked)}/{len(ACHIEVEMENTS)}',
                                   True, COLORS['GREEN'])
        self.screen.blit(summary, (65, 90))
        for index, (achievement_id, item) in enumerate(ACHIEVEMENTS.items()):
            col, row = index % 2, index // 2
            rect = pygame.Rect(65 + col * 420, 125 + row * 65, 395, 54)
            done = achievement_id in unlocked
            class_ok = item.get('class') in (None, player.character_class)
            bg = (32, 58, 48) if done else (34, 35, 45)
            pygame.draw.rect(self.screen, bg, rect, border_radius=5)
            pygame.draw.rect(self.screen, COLORS['GREEN'] if done else COLORS['GRAY'], rect, 1,
                             border_radius=5)
            mark = 'COMPLETO' if done else ('OTRA CLASE' if not class_ok else
                                            f"{min(progress(player, item), item['target'])}/{item['target']}")
            name = self.font.render(item['name'], True,
                                    COLORS['GREEN'] if done else COLORS['WHITE'])
            self.screen.blit(name, (rect.x + 10, rect.y + 5))
            badge = self.font_small.render(mark, True, COLORS['YELLOW'] if class_ok else COLORS['GRAY'])
            self.screen.blit(badge, (rect.right - badge.get_width() - 10, rect.y + 7))
            desc = self.font_small.render(item['description'], True, COLORS['GRAY'])
            self.screen.blit(desc, (rect.x + 10, rect.y + 31))
        hint = self.font_small.render('ESC: cerrar', True, COLORS['GRAY'])
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 585))

    SETTINGS_TABS = (('graphics', 'Gráficos'), ('audio', 'Audio'),
                     ('accessibility', 'Accesibilidad'), ('controls', 'Controles'))
    SETTINGS_TAB_Y = 105
    SETTINGS_BACK = (70, 555, 150, 34)
    SETTINGS_RESET = (740, 555, 150, 34)
    SETTINGS_REBIND_X = (115, 495)
    SETTINGS_REBIND_W, SETTINGS_REBIND_Y0 = 350, 165
    SETTINGS_REBIND_H, SETTINGS_REBIND_GAP = 26, 5

    def _settings_button(self, rect, label, active=False):
        hover = rect.collidepoint(self.mouse_pos())
        bg = COLORS['YELLOW'] if active else ((70, 70, 95) if hover else (45, 45, 60))
        fg = COLORS['BLACK'] if active else COLORS['WHITE']
        pygame.draw.rect(self.screen, bg, rect, border_radius=5)
        pygame.draw.rect(self.screen, COLORS['YELLOW'] if hover else COLORS['GRAY'], rect, 1,
                         border_radius=5)
        text = self.font.render(label, True, fg)
        self.screen.blit(text, (rect.centerx - text.get_width() // 2,
                                rect.centery - text.get_height() // 2))

    def draw_settings(self, config, tab, rebinding=None):
        from systems import controls
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(220)
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(45, 30, SCREEN_WIDTH - 90, SCREEN_HEIGHT - 60)
        pygame.draw.rect(self.screen, (20, 20, 30), panel, border_radius=8)
        pygame.draw.rect(self.screen, COLORS['GRAY'], panel, 2, border_radius=8)
        title = self.font_title.render('CONFIGURACIÓN', True, COLORS['YELLOW'])
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 48))
        for index, (tab_id, label) in enumerate(self.SETTINGS_TABS):
            rect = pygame.Rect(120 + index * 180, self.SETTINGS_TAB_Y, 160, 36)
            self._settings_button(rect, label, tab == tab_id)

        if tab == 'graphics':
            resolution = ' × '.join(str(value) for value in config['resolution'])
            self._settings_button(pygame.Rect(280, 205, 400, 44), f'Resolución: {resolution}')
            mode = 'Pantalla completa' if config['fullscreen'] else 'Ventana'
            self._settings_button(pygame.Rect(280, 270, 400, 44), f'Modo: {mode}')
            quality = 'Alta' if config.get('effects_quality', 'high') == 'high' else 'Baja'
            self._settings_button(pygame.Rect(280, 335, 400, 44),
                                  f'Calidad de efectos: {quality}')
            minimap_labels = {'full': 'Completo', 'compact': 'Reducido', 'hidden': 'Oculto'}
            self._settings_button(pygame.Rect(280, 400, 400, 44),
                                  f"Minimapa: {minimap_labels[config.get('minimap_mode', 'full')]}")
            note = self.font_small.render('Los cambios gráficos se aplican inmediatamente.', True,
                                          COLORS['GRAY'])
            self.screen.blit(note, (SCREEN_WIDTH // 2 - note.get_width() // 2, 465))
        elif tab == 'audio':
            labels = (('master_volume', 'General'), ('music_volume', 'Música'),
                      ('sfx_volume', 'Efectos'))
            for index, (key, label) in enumerate(labels):
                y = 190 + index * 75
                value = int(round(config[key] * 100))
                text = self.font.render(f'{label}: {value}%', True, COLORS['WHITE'])
                self.screen.blit(text, (280, y + 7))
                self._settings_button(pygame.Rect(545, y, 48, 38), '−')
                self._settings_button(pygame.Rect(605, y, 48, 38), '+')
        elif tab == 'accessibility':
            labels = (
                ('text_size', f"Texto: {'Grande' if config.get('text_size') == 'large' else 'Normal'}"),
                ('high_contrast', f"Alto contraste: {'Sí' if config.get('high_contrast') else 'No'}"),
                ('reduced_motion', f"Movimiento reducido: {'Sí' if config.get('reduced_motion') else 'No'}"),
                ('screen_shake', f"Sacudida: {int(config.get('screen_shake', 1.0) * 100)}%"),
                ('reduced_flashes', f"Destellos reducidos: {'Sí' if config.get('reduced_flashes') else 'No'}"),
            )
            for index, (_key, label) in enumerate(labels):
                self._settings_button(pygame.Rect(280, 170 + index * 62, 400, 42), label)
        else:
            rows_per_col = (len(controls.REBINDABLE) + len(self.SETTINGS_REBIND_X) - 1) // len(self.SETTINGS_REBIND_X)
            for index, action in enumerate(controls.REBINDABLE):
                col, row = index // rows_per_col, index % rows_per_col
                x = self.SETTINGS_REBIND_X[col]
                y = self.SETTINGS_REBIND_Y0 + row * (self.SETTINGS_REBIND_H + self.SETTINGS_REBIND_GAP)
                rect = pygame.Rect(x, y, self.SETTINGS_REBIND_W, self.SETTINGS_REBIND_H)
                waiting = rebinding == action
                keys = '+'.join(controls.key_label(code) for code in controls.codes(action))
                label = f'{controls.action_label(action)}: {"pulsa una tecla" if waiting else keys}'
                self._settings_button(rect, label, waiting)

        self._settings_button(pygame.Rect(*self.SETTINGS_BACK), 'Volver')
        self._settings_button(pygame.Rect(*self.SETTINGS_RESET), 'Restablecer')

    def settings_action_at(self, pos, tab):
        from systems import controls
        for index, (tab_id, _label) in enumerate(self.SETTINGS_TABS):
            if pygame.Rect(120 + index * 180, self.SETTINGS_TAB_Y, 160, 36).collidepoint(pos):
                return ('tab', tab_id)
        if pygame.Rect(*self.SETTINGS_BACK).collidepoint(pos):
            return ('back', None)
        if pygame.Rect(*self.SETTINGS_RESET).collidepoint(pos):
            return ('reset_settings', None)
        if tab == 'graphics':
            if pygame.Rect(280, 205, 400, 44).collidepoint(pos):
                return ('resolution', None)
            if pygame.Rect(280, 270, 400, 44).collidepoint(pos):
                return ('fullscreen', None)
            if pygame.Rect(280, 335, 400, 44).collidepoint(pos):
                return ('effects_quality', None)
            if pygame.Rect(280, 400, 400, 44).collidepoint(pos):
                return ('minimap_mode', None)
        elif tab == 'audio':
            keys = ('master_volume', 'music_volume', 'sfx_volume')
            for index, key in enumerate(keys):
                y = 190 + index * 75
                if pygame.Rect(545, y, 48, 38).collidepoint(pos):
                    return ('volume', (key, -0.1))
                if pygame.Rect(605, y, 48, 38).collidepoint(pos):
                    return ('volume', (key, 0.1))
        elif tab == 'accessibility':
            keys = ('text_size', 'high_contrast', 'reduced_motion',
                    'screen_shake', 'reduced_flashes')
            for index, key in enumerate(keys):
                if pygame.Rect(280, 170 + index * 62, 400, 42).collidepoint(pos):
                    return ('accessibility', key)
        elif tab == 'controls':
            rows_per_col = (len(controls.REBINDABLE) + len(self.SETTINGS_REBIND_X) - 1) // len(self.SETTINGS_REBIND_X)
            for index, action in enumerate(controls.REBINDABLE):
                col, row = index // rows_per_col, index % rows_per_col
                x = self.SETTINGS_REBIND_X[col]
                y = self.SETTINGS_REBIND_Y0 + row * (self.SETTINGS_REBIND_H + self.SETTINGS_REBIND_GAP)
                if pygame.Rect(x, y, self.SETTINGS_REBIND_W,
                               self.SETTINGS_REBIND_H).collidepoint(pos):
                    return ('rebind', action)
        return None

    # --- Mapa del mundo ---
    MAP_RECT = pygame.Rect(70, 170, SCREEN_WIDTH - 140, 230)
    MAP_ZONE_COLORS = {
        'meadow': (75, 145, 85),
        'caves': (95, 115, 135),
        'ruins': (150, 115, 70),
        'sanctum': (105, 100, 165),
        'peak': (90, 155, 180),
    }

    def draw_minimap(self, player, enemies, current_room, mode='full'):
        if mode == 'hidden' or current_room is None:
            return
        from constants import TILE_SIZE
        from world.world_data import (BOSS_ARENAS, CHECKPOINT_DEFS, DIVIDERS,
                                      ROOM_DEFS, ZONE_DEFS)
        room = next((item for item in ROOM_DEFS if item['id'] == current_room), None)
        if room is None:
            return
        width = 150 if mode == 'compact' else 220
        rect = pygame.Rect(SCREEN_WIDTH - width - 18, 78, width, 76)
        pygame.draw.rect(self.screen, (12, 15, 21), rect, border_radius=5)
        pygame.draw.rect(self.screen, (115, 120, 135), rect, 1, border_radius=5)
        zone = next(item for item in ZONE_DEFS if item['id'] == room['zone_id'])
        span = max(1, zone['x1'] - zone['x0'] + 1)

        def map_x(tx):
            return rect.x + 8 + int((tx - zone['x0']) / span * (rect.w - 16))

        y = rect.centery + 8
        for item in ROOM_DEFS:
            if item['zone_id'] != zone['id'] or item['id'] not in player.explored_rooms:
                continue
            x0, x1 = map_x(item['x0']), map_x(item['x1'] + 1)
            color = (95, 165, 210) if item['id'] == current_room else (65, 72, 88)
            pygame.draw.rect(self.screen, color, pygame.Rect(x0, y - 8, max(3, x1 - x0), 16),
                             border_radius=2)
        for divider in DIVIDERS:
            if zone['x0'] <= divider['tx'] <= zone['x1']:
                color = (100, 225, 140) if divider['gate_id'] in player.opened_gates else (235, 90, 75)
                pygame.draw.line(self.screen, color, (map_x(divider['tx']), y - 11),
                                 (map_x(divider['tx']), y + 11), 2)
        for checkpoint in CHECKPOINT_DEFS:
            if checkpoint['zone_id'] == zone['id'] and checkpoint['id'] in player.unlocked_checkpoints:
                pygame.draw.circle(self.screen, (100, 225, 255), (map_x(checkpoint['tx']), y), 4)
        for arena in BOSS_ARENAS:
            if zone['x0'] <= arena['trigger_tx'] <= zone['x1'] and arena['id'] not in player.boss_defeated_ids:
                pygame.draw.rect(self.screen, (235, 80, 95),
                                 pygame.Rect(map_x(arena['trigger_tx']) - 3, y - 3, 7, 7))
        player_tx = player.rect.centerx / TILE_SIZE
        objectives = [divider['tx'] for divider in DIVIDERS
                      if zone['x0'] <= divider['tx'] <= zone['x1']
                      and divider['gate_id'] not in player.opened_gates]
        objectives.extend(arena['trigger_tx'] for arena in BOSS_ARENAS
                          if zone['x0'] <= arena['trigger_tx'] <= zone['x1']
                          and arena['id'] not in player.boss_defeated_ids)
        if objectives:
            objective_x = map_x(min(objectives, key=lambda tx: abs(tx - player_tx)))
            pygame.draw.circle(self.screen, COLORS['YELLOW'], (objective_x, y), 7, 1)
        px = map_x(player_tx)
        pygame.draw.polygon(self.screen, COLORS['YELLOW'], ((px, y - 13), (px - 5, y - 19), (px + 5, y - 19)))
        if mode == 'full':
            for enemy in enemies:
                etx = enemy.rect.centerx / TILE_SIZE
                if room['x0'] <= etx <= room['x1'] and abs(enemy.rect.centerx - player.rect.centerx) < 420:
                    pygame.draw.circle(self.screen, (245, 85, 80), (map_x(etx), y + 17), 2)
            label = self.font_small.render(room['name'], True, COLORS['WHITE'])
            self.screen.blit(label, (rect.x + 7, rect.y + 5))

    def _world_map_zone_rects(self):
        from world.world_data import MAP_WIDTH, ZONE_DEFS
        rects = []
        for zone in ZONE_DEFS:
            left = self.MAP_RECT.x + round(zone['x0'] / MAP_WIDTH * self.MAP_RECT.w)
            right_tx = min(MAP_WIDTH, zone['x1'] + 1)
            right = self.MAP_RECT.x + round(right_tx / MAP_WIDTH * self.MAP_RECT.w)
            rects.append((zone, pygame.Rect(left, self.MAP_RECT.y,
                                            max(1, right - left), self.MAP_RECT.h)))
        return rects

    def _world_map_x(self, tx):
        from world.world_data import MAP_WIDTH
        return self.MAP_RECT.x + round(max(0, min(MAP_WIDTH, tx)) / MAP_WIDTH
                                      * self.MAP_RECT.w)

    def draw_world_map(self, player, selected_zone=None):
        from systems.secret_data import SECRETS
        from systems.encounter_data import ENCOUNTERS
        from systems.route_data import ROUTES
        from world.world_data import (ABILITY_NAMES, BOSS_ARENAS, CHECKPOINT_DEFS,
                                      DIVIDERS, GATE_DEFS, PLATFORMS, ROOM_DEFS,
                                      ZONE_DEFS)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(225)
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(35, 25, SCREEN_WIDTH - 70, SCREEN_HEIGHT - 50)
        pygame.draw.rect(self.screen, (18, 20, 28), panel, border_radius=8)
        pygame.draw.rect(self.screen, COLORS['GRAY'], panel, 2, border_radius=8)
        title = self.font_title.render('MAPA DEL REINO', True, COLORS['YELLOW'])
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 43))
        explored = player.explored_zones
        explored_rooms = getattr(player, 'explored_rooms', set())
        progress = self.font.render(
            f'Explorado: {len(explored)}/{len(ZONE_DEFS)} zonas · '
            f'{len(explored_rooms)}/{len(ROOM_DEFS)} salas',
                                    True, COLORS['GREEN'])
        self.screen.blit(progress, (70, 112))

        pygame.draw.rect(self.screen, (12, 14, 20), self.MAP_RECT)
        for zone, rect in self._world_map_zone_rects():
            known = zone['id'] in explored
            color = self.MAP_ZONE_COLORS.get(zone['id'], (90, 90, 100)) if known else (30, 32, 42)
            pygame.draw.rect(self.screen, color, rect)
            border = COLORS['YELLOW'] if selected_zone == zone['id'] else (75, 78, 90)
            pygame.draw.rect(self.screen, border, rect, 3 if selected_zone == zone['id'] else 1)
            label = zone['name'] if known else '???'
            text = self.font_small.render(label, True, COLORS['WHITE'] if known else COLORS['GRAY'])
            self.screen.blit(text, (rect.centerx - text.get_width() // 2, rect.y + 12))

        # Cada tercio de zona representa una sala y se revela por separado.
        for room in ROOM_DEFS:
            x0 = self._world_map_x(room['x0'])
            x1 = self._world_map_x(room['x1'] + 1)
            known = room['id'] in explored_rooms
            y = self.MAP_RECT.y + 43
            pygame.draw.rect(self.screen, (225, 225, 235) if known else (58, 60, 70),
                             pygame.Rect(x0 + 2, y, max(2, x1 - x0 - 4), 5),
                             border_radius=2)
            if room['x0'] > 0:
                pygame.draw.line(self.screen, (105, 108, 125),
                                 (x0, self.MAP_RECT.y + 38),
                                 (x0, self.MAP_RECT.bottom - 18), 1)
            if room['id'] in ENCOUNTERS and known:
                done = room['id'] in getattr(player, 'completed_encounters', set())
                pygame.draw.circle(self.screen,
                                   (105, 235, 145) if done else (255, 185, 75),
                                   ((x0 + x1) // 2, y + 17), 4)

        # Plataformas conocidas aportan la silueta real del escenario.
        for platform in PLATFORMS:
            zone = next((z for z in ZONE_DEFS if z['x0'] <= platform['x0'] <= z['x1']), None)
            if zone is None or zone['id'] not in explored:
                continue
            x0, x1 = self._world_map_x(platform['x0']), self._world_map_x(platform['x1'] + 1)
            y = self.MAP_RECT.bottom - 35 - int((47 - platform['y']) * 4)
            pygame.draw.line(self.screen, (210, 215, 220), (x0, y), (x1, y), 3)

        for divider in DIVIDERS:
            left_zone = next((z for z in ZONE_DEFS if z['x1'] == divider['tx']), None)
            right_zone = next((z for z in ZONE_DEFS if z['x0'] == divider['tx'] + 1), None)
            if not ((left_zone and left_zone['id'] in explored)
                    or (right_zone and right_zone['id'] in explored)):
                continue
            x = self._world_map_x(divider['tx'])
            opened = divider['gate_id'] in player.opened_gates
            pygame.draw.line(self.screen, (100, 230, 150) if opened else (235, 105, 80),
                             (x, self.MAP_RECT.y + 58), (x, self.MAP_RECT.bottom - 25), 4)

        for checkpoint in CHECKPOINT_DEFS:
            if checkpoint['zone_id'] not in explored:
                continue
            x = self._world_map_x(checkpoint['tx'])
            unlocked = checkpoint['id'] in player.unlocked_checkpoints
            color = (100, 230, 255) if unlocked else (110, 110, 120)
            pygame.draw.circle(self.screen, color, (x, self.MAP_RECT.bottom - 25), 7)
            pygame.draw.circle(self.screen, COLORS['BLACK'], (x, self.MAP_RECT.bottom - 25), 7, 1)

        for route_id, route in ROUTES.items():
            if route['zone_id'] not in explored:
                continue
            x = self._world_map_x(route['goal'][0])
            done = route_id in getattr(player, 'completed_routes', set())
            unlocked = route['required'] in player.unlocked_abilities
            color = (105, 235, 145) if done else ((115, 190, 245) if unlocked
                                                   else (95, 96, 110))
            pygame.draw.polygon(self.screen, color,
                                ((x, self.MAP_RECT.y + 60),
                                 (x - 5, self.MAP_RECT.y + 69),
                                 (x + 5, self.MAP_RECT.y + 69)))

        for arena in BOSS_ARENAS:
            zone = next((z for z in ZONE_DEFS if z['x0'] <= arena['trigger_tx'] <= z['x1']), None)
            if zone is None or zone['id'] not in explored:
                continue
            x = self._world_map_x(arena['trigger_tx'])
            defeated = arena['id'] in player.boss_defeated_ids
            color = (110, 220, 130) if defeated else (255, 85, 85)
            pygame.draw.rect(self.screen, color, pygame.Rect(x - 6, self.MAP_RECT.y + 72, 12, 12),
                             border_radius=2)

        player_tx = player.rect.centerx / TILE_SIZE
        px = self._world_map_x(player_tx)
        pygame.draw.polygon(self.screen, COLORS['YELLOW'],
                            ((px, self.MAP_RECT.bottom - 55),
                             (px - 7, self.MAP_RECT.bottom - 68),
                             (px + 7, self.MAP_RECT.bottom - 68)))

        selected = next((zone for zone in ZONE_DEFS
                         if zone['id'] == selected_zone and zone['id'] in explored), None)
        if selected:
            checkpoints = [cp for cp in CHECKPOINT_DEFS if cp['zone_id'] == selected['id']]
            gates = [d for d in DIVIDERS if selected['x0'] - 1 <= d['tx'] <= selected['x1']]
            heading = self.font_big.render(selected['name'], True,
                                           self.MAP_ZONE_COLORS.get(selected['id'], COLORS['WHITE']))
            self.screen.blit(heading, (70, 430))
            unlocked = sum(cp['id'] in player.unlocked_checkpoints for cp in checkpoints)
            zone_secrets = [secret_id for secret_id, secret in SECRETS.items()
                            if secret['zone_id'] == selected['id']]
            found_secrets = sum(secret_id in player.discovered_secrets
                                for secret_id in zone_secrets)
            zone_rooms = [room for room in ROOM_DEFS
                          if room['zone_id'] == selected['id']]
            found_rooms = sum(room['id'] in explored_rooms for room in zone_rooms)
            zone_encounters = [room['id'] for room in zone_rooms
                               if room['id'] in ENCOUNTERS]
            won_encounters = sum(room_id in player.completed_encounters
                                 for room_id in zone_encounters)
            zone_routes = [route_id for route_id, route in ROUTES.items()
                           if route['zone_id'] == selected['id']]
            won_routes = sum(route_id in player.completed_routes
                             for route_id in zone_routes)
            details = (f'Santuarios: {unlocked}/{len(checkpoints)}  |  '
                       f'Secretos: {found_secrets}/{len(zone_secrets)}  |  '
                       f'Desafíos: {won_encounters}/{len(zone_encounters)}  |  '
                       f'Rutas: {won_routes}/{len(zone_routes)}')
            self.screen.blit(self.font.render(details, True, COLORS['WHITE']), (70, 472))
            requirements = ', '.join(
                ABILITY_NAMES[GATE_DEFS[divider['gate_id']]['required']]
                for divider in gates
                if divider['gate_id'] not in player.opened_gates
            )
            if requirements:
                self.screen.blit(self.font_small.render(f'Sellos pendientes: {requirements}', True,
                                                        (235, 150, 100)), (70, 505))

        legend = self.font_small.render('▲ Tú   ● Santuario   ■ Jefe   Rojo: puerta cerrada   Verde: abierta',
                                        True, COLORS['GRAY'])
        self.screen.blit(legend, (70, 545))
        hint = self.font_small.render('Click: inspeccionar · Click en santuario activo: viajar · H/ESC: cerrar',
                                      True, COLORS['GRAY'])
        self.screen.blit(hint, (SCREEN_WIDTH - 70 - hint.get_width(), 582))

    def world_map_action_at(self, player, pos):
        from world.world_data import CHECKPOINT_DEFS
        for checkpoint in CHECKPOINT_DEFS:
            if (checkpoint['zone_id'] in player.explored_zones
                    and checkpoint['id'] in player.unlocked_checkpoints):
                x = self._world_map_x(checkpoint['tx'])
                marker = pygame.Rect(x - 12, self.MAP_RECT.bottom - 37, 24, 24)
                if marker.collidepoint(pos):
                    return ('travel', checkpoint['id'])
        for zone, rect in self._world_map_zone_rects():
            if zone['id'] in player.explored_zones and rect.collidepoint(pos):
                return ('zone', zone['id'])
        return None

    def draw_intro(self, page, num, total):
        title, lines = page
        s = self.screen
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(215)
        s.blit(overlay, (0, 0))
        panel = pygame.Rect(180, 150, SCREEN_WIDTH - 360, 300)
        pygame.draw.rect(s, (20, 20, 30), panel, border_radius=10)
        pygame.draw.rect(s, COLORS['YELLOW'], panel, 2, border_radius=10)
        t = self.font_title.render(title, True, COLORS['YELLOW'])
        s.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 175))
        y = 235
        for line in lines:
            lt = self.font.render(line, True, COLORS['WHITE'])
            s.blit(lt, (SCREEN_WIDTH // 2 - lt.get_width() // 2, y))
            y += 32
        hint = self.font_small.render(f"Click o tecla para continuar ({num}/{total}) · ESC salta", True, COLORS['GRAY'])
        s.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 400))

    # --- Bestiario ---
    BEST_TABS = [('common', 'Comunes'), ('elite', 'Élites'), ('mini', 'Minijefes'), ('boss', 'Jefes')]
    BEST_TAB_Y, BEST_TAB_W, BEST_TAB_H = 78, 150, 30
    BEST_Y0, BEST_H, BEST_GAP = 125, 64, 6

    def _bestiary_rows(self, player, tab):
        """Filas (entry, kills) de la pestaña. Élites agregadas por afijo."""
        from systems.bestiary import CATALOG
        if tab == 'elite':
            agg = {}
            for key, e in CATALOG.items():
                if e['category'] != 'elite':
                    continue
                affix = key.split(':')[1]
                a = agg.setdefault(affix, {'kills': 0, 'name': None, 'color': e['color'],
                                           'trait': e['trait'], 'tip': e['tip']})
                a['kills'] += player.bestiary.get(key, 0)
                if a['name'] is None:
                    from systems.balance_data import ELITE_AFFIXES
                    af = next(x for x in ELITE_AFFIXES if x['id'] == affix)
                    a['name'] = f"Élites {af['name']}"
                    a['stats'] = f"×{af['hp']} HP · ×{af['dmg']} DMG · ×{af['xp']} XP"
            rows = []
            for affix, a in agg.items():
                rows.append({'name': a['name'], 'kills': a['kills'], 'color': a['color'],
                             'stats': a.get('stats', ''), 'zones': 'Todas (más al este)',
                             'trait': a['trait'], 'tip': a['tip']})
            return rows
        rows = []
        for key, e in CATALOG.items():
            if e['category'] != tab:
                continue
            kills = player.bestiary.get(key, 0)
            rows.append({'name': e['name'], 'kills': kills, 'color': e['color'],
                         'stats': f"{e['hp']} HP · {e['dmg']} DMG · {e['xp']} XP",
                         'zones': e['zones'], 'trait': e['trait'], 'tip': e['tip']})
        return rows

    def draw_bestiary(self, player, tab='common'):
        from systems.bestiary import total_entries, unlocked_count
        s = self.screen
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(220)
        s.blit(overlay, (0, 0))
        panel = pygame.Rect(40, 30, SCREEN_WIDTH - 80, SCREEN_HEIGHT - 60)
        pygame.draw.rect(s, (20, 20, 30), panel, border_radius=10)
        pygame.draw.rect(s, COLORS['GRAY'], panel, 2, border_radius=10)
        title = self.font_title.render("BESTIARIO", True, COLORS['YELLOW'])
        s.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 40))
        prog = self.font.render(f"Descubiertos: {unlocked_count(player.bestiary)}/{total_entries()}",
                                True, COLORS['GREEN'])
        s.blit(prog, (60, 48))
        mouse_pos = self.mouse_pos()
        tx0 = SCREEN_WIDTH // 2 - (len(self.BEST_TABS) * (self.BEST_TAB_W + 10)) // 2
        for i, (tid, tlabel) in enumerate(self.BEST_TABS):
            r = pygame.Rect(tx0 + i * (self.BEST_TAB_W + 10), self.BEST_TAB_Y,
                            self.BEST_TAB_W, self.BEST_TAB_H)
            active = (tab == tid)
            bg = COLORS['YELLOW'] if active else ((70, 70, 95) if r.collidepoint(mouse_pos) else (45, 45, 60))
            pygame.draw.rect(s, bg, r, border_radius=5)
            t = self.font.render(tlabel, True, COLORS['BLACK'] if active else COLORS['WHITE'])
            s.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
        for idx, row in enumerate(self._bestiary_rows(player, tab)):
            y = self.BEST_Y0 + idx * (self.BEST_H + self.BEST_GAP)
            rect = pygame.Rect(60, y, SCREEN_WIDTH - 120, self.BEST_H)
            known = row['kills'] > 0
            pygame.draw.rect(s, (40, 40, 55) if known else (30, 30, 38), rect, border_radius=6)
            pygame.draw.rect(s, row['color'] if known else (70, 70, 70), rect, 2, border_radius=6)
            if not known:
                t = self.font_big.render("???  (derrota uno para registrarlo)", True, (110, 110, 110))
                s.blit(t, (rect.x + 14, y + 16))
                continue
            s.blit(self.font_big.render(f"{row['name']}  x{row['kills']}", True, row['color']),
                   (rect.x + 12, y + 4))
            s.blit(self.font_small.render(f"{row['stats']}  |  {row['zones']}  |  {row['trait']}",
                                          True, COLORS['GRAY']), (rect.x + 12, y + 30))
            s.blit(self.font_small.render(row['tip'][:78], True, COLORS['GREEN']), (rect.x + 12, y + 46))
        help_t = self.font.render("J/ESC: cerrar", True, COLORS['GRAY'])
        s.blit(help_t, (SCREEN_WIDTH // 2 - help_t.get_width() // 2, SCREEN_HEIGHT - 42))

    def bestiary_tab_at(self, mouse_pos):
        tx0 = SCREEN_WIDTH // 2 - (len(self.BEST_TABS) * (self.BEST_TAB_W + 10)) // 2
        for i, (tid, _) in enumerate(self.BEST_TABS):
            r = pygame.Rect(tx0 + i * (self.BEST_TAB_W + 10), self.BEST_TAB_Y,
                            self.BEST_TAB_W, self.BEST_TAB_H)
            if r.collidepoint(mouse_pos):
                return tid
        return None

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(180)
        self.screen.blit(overlay, (0, 0))
        go = self.font_title.render("GAME OVER", True, COLORS['RED'])
        rt = self.font.render("R: despertar en el santuario (conservas todo)  |  ESC: menu", True, COLORS['WHITE'])
        self.screen.blit(go, (SCREEN_WIDTH // 2 - go.get_width() // 2, SCREEN_HEIGHT // 2 - 40))
        self.screen.blit(rt, (SCREEN_WIDTH // 2 - rt.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

    # --- Inventario / Equipo ---
    INV_SLOTS = ['weapon', 'helmet', 'armor', 'boots', 'accessory']
    INV_SLOT_NAMES = {'weapon': 'Arma', 'helmet': 'Casco', 'armor': 'Armadura', 'boots': 'Botas', 'accessory': 'Accesorio'}

    def _rarity_color(self, rarity):
        try:
            from systems.items import RARITIES
            return RARITIES.get(rarity, {}).get('color', (255, 255, 255))
        except Exception:
            return (255, 255, 255)

    def draw_inventory(self, player, message=""):
        from systems.items import format_stats
        s = self.screen
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(220)
        s.blit(overlay, (0, 0))
        panel = pygame.Rect(40, 30, SCREEN_WIDTH - 80, SCREEN_HEIGHT - 60)
        pygame.draw.rect(s, (20, 20, 30), panel, border_radius=10)
        pygame.draw.rect(s, COLORS['GRAY'], panel, 2, border_radius=10)
        title = self.font_title.render(f"EQUIPO - {player.name.upper()}  |  Oro: {player.gold}", True, COLORS['YELLOW'])
        s.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 40))
        if message:
            m = self.font.render(message, True, COLORS['GREEN'])
            s.blit(m, (SCREEN_WIDTH // 2 - m.get_width() // 2, 80))
        s.blit(self.font.render("Equipado (click para desequipar):", True, COLORS['WHITE']), (60, 115))
        s.blit(self.font.render(f"Mochila ({len(player.inventory)}) (click para equipar):", True, COLORS['WHITE']), (400, 115))
        # Equipado
        for i, slot in enumerate(self.INV_SLOTS):
            y = 140 + i * 78
            rect = pygame.Rect(60, y, 300, 70)
            it = player.equipment.get(slot)
            pygame.draw.rect(s, (40, 40, 55), rect, border_radius=6)
            pygame.draw.rect(s, self._rarity_color(it['rarity']) if it else (70, 70, 70), rect, 2, border_radius=6)
            s.blit(self.font_small.render(self.INV_SLOT_NAMES[slot], True, COLORS['GRAY']), (70, y + 5))
            if it:
                icon = self._item_icon(it)
                if icon is not None:
                    s.blit(icon, (70, y + 25))
                s.blit(self.font.render(it['name'][:24], True, self._rarity_color(it['rarity'])), (112, y + 22))
                s.blit(self.font_small.render(format_stats(it.get('stats', {}))[:42], True, COLORS['GREEN']), (112, y + 45))
            else:
                s.blit(self.font_small.render("(vacio)", True, (110, 110, 110)), (70, y + 30))
        # Inventario (primeros 7)
        for idx, it in enumerate(player.inventory[:7]):
            y = 140 + idx * 60
            rect = pygame.Rect(400, y, SCREEN_WIDTH - 480, 54)
            hover = rect.collidepoint(self.mouse_pos())
            pygame.draw.rect(s, (55, 55, 75) if hover else (40, 40, 55), rect, border_radius=6)
            pygame.draw.rect(s, self._rarity_color(it['rarity']), rect, 1, border_radius=6)
            icon = self._item_icon(it)
            if icon is not None:
                s.blit(icon, (408, y + 9))
            s.blit(self.font.render(f"{it['name'][:25]} Nv{it.get('level',1)}", True, self._rarity_color(it['rarity'])), (450, y + 4))
            s.blit(self.font_small.render(f"[{self.INV_SLOT_NAMES.get(it['slot'], it['slot'])}] " + format_stats(it.get('stats', {}))[:48], True, COLORS['GRAY']), (450, y + 28))
        if len(player.inventory) > 7:
            s.blit(self.font_small.render(f"... y {len(player.inventory)-7} mas", True, COLORS['GRAY']), (400, 140 + 7 * 60))
        # Stats totales
        st = self.font_small.render(f"DMG {player.damage} | HP {player.health}/{player.max_health} | VEL {player.speed:.0f} | CRIT {player._stat_multipliers.get('crit_chance',0)*100:.0f}% | EVA {player._stat_multipliers.get('evasion',0)*100:.0f}% | XP +{player._stat_multipliers.get('xp_gain',1.0)*100-100:.0f}%", True, COLORS['WHITE'])
        s.blit(st, (60, SCREEN_HEIGHT - 65))
        h = self.font_small.render("I: Cerrar  |  Click mochila: equipar  |  Click equipo: desequipar", True, COLORS['GRAY'])
        s.blit(h, (SCREEN_WIDTH // 2 - h.get_width() // 2, SCREEN_HEIGHT - 42))

    def inventory_item_at(self, player, mouse_pos):
        for idx, it in enumerate(player.inventory[:7]):
            y = 140 + idx * 60
            if pygame.Rect(400, y, SCREEN_WIDTH - 480, 54).collidepoint(mouse_pos):
                return it.get('id')
        return None

    def equipped_slot_at(self, mouse_pos):
        for i, slot in enumerate(self.INV_SLOTS):
            y = 140 + i * 78
            if pygame.Rect(60, y, 300, 70).collidepoint(mouse_pos):
                return slot
        return None
