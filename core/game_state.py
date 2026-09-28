"""Lifecycle, save loading, respawn, and new-game-plus coordination."""

import random

import pygame

from constants import PLAYER_START_POS, TILE_SIZE
from entities.enemy import Enemy
from entities.player import Player
from systems import audio, controls
from systems.balance_data import ELITE_AFFIXES, MINIBOSS_DEFS
from systems.items import generate_item, starting_kit
from core.game_data import (ENEMY_SPAWNS, LOAD_SPAWNS, MINIBOSS_SPAWNS,
    TOTAL_BOSSES)
from core.screen_state import GameScreen
from world.world_data import LOOT_SPAWNS


class GameStateMixin:
    def intro_pages(self):
        atk = "+".join(controls.key_label(c) for c in controls.codes('attack'))
        skl = "+".join(controls.key_label(c) for c in controls.codes('skills'))
        return [
            ("EL REINO FRACTURADO", [
                "La niebla devoró el reino y los santuarios callaron.",
                "Eres el último Errante. Recupera las 5 zonas,",
                "despierta los santuarios y destruye a los 3 jefes.",
            ]),
            ("CÓMO JUGAR", [
                f"Muévete y salta. Ataca con {atk}.",
                f"Sube de nivel y gasta puntos en ({skl}).",
                "El equipo se compra, se mejora y se forja.",
            ]),
            ("MUERTE Y PROGRESO", [
                "Al morir despiertas en el último santuario: no pierdes nada.",
                "Cada puerta sellada exige una habilidad concreta.",
                "Completa los 3 jefes y llegará el Nuevo Juego+.",
            ]),
        ]

    def current_objective(self):
        p = self.player
        if p is None:
            return ""
        from systems.npc_data import NPCS
        from systems.quest_data import QUESTS, quest_status
        for quest_id, quest in QUESTS.items():
            status = quest_status(p, quest_id)
            if status == 'ready':
                return f"Entrega {quest['title']} a {NPCS[quest['giver']]['name'].split(',')[0]}"
            if status == 'active':
                return quest['summary']
        done = p.boss_defeated_ids
        gates = p.opened_gates
        if len(done) >= TOTAL_BOSSES:
            return f"¡Juego completado! P: NG+{p.ng_plus + 1}"
        if 'void_heart' not in done and 'sanctum_guardian' in done:
            return "El Vacío aguarda al fondo del Santuario"
        if 'sanctum_guardian' not in done and 'gate_rune' in gates:
            return "Santuario: derrota al Guardián"
        if 'cavern_mother' in done and 'gate_shadow' not in gates:
            return "Abre la Puerta Sombra (Dash) · Ruinas al este"
        if 'gate_wind' in gates and 'cavern_mother' not in done:
            return "Cavernas: derrota a la Madre de la Ciénaga"
        if not gates:
            return "Sube de nivel y abre la Puerta Vendaval (Doble Salto)"
        return "Explora, equípate y derrota jefes"

    def create_player(self, char_class):
        self.combat_visuals.accents.clear()
        self.player = Player(character_class=char_class)
        self.game_map.reset_secrets()
        # Kit inicial auto-equipado
        for kit_item in starting_kit(char_class):
            self.player.add_item(kit_item)
        # Auto-equipar kit
        for it in list(self.player.inventory):
            self.player.equip_item(it['id'])
        self.game_map.apply_opened(self.player.opened_gates)
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.all_sprites.add(self.player)
        self._spawn_enemies(ENEMY_SPAWNS)
        self.drops = []
        for loot in LOOT_SPAWNS:
            item = generate_item(loot['level'], loot['slot'], loot['rarity'])
            item['name'] = loot['name']
            self.drops.append({
                'item': item,
                'rect': pygame.Rect(loot['tx'] * TILE_SIZE, loot['ty'] * TILE_SIZE, 14, 14),
                'vy': 0.0,
                'gold': 0,
                't': 0.0,
            })
        self.set_screen(GameScreen.INTRO)
        self.rebinding = None
        self._go_sound = False
        self.intro_page = 0
        self.sign_text = ""
        self.boss = None
        self.projectiles = pygame.sprite.Group()
        self.ally_shots = pygame.sprite.Group()
        self.pending_meteors = []
        self.blizzards = []
        self.death_visuals = []
        self.orb_angle = 0.0
        self.boss_banner_t = 0.0
        self.boss_phase_t = 0.0
        self.boss_phase_text = ""
        self.victory_t = 0.0
        z = self.game_map.get_zone_at(self.player.rect.centerx)
        self.current_zone = z['id']
        self.player.explored_zones.add(z['id'])
        self.map_selected_zone = z['id']
        self.snap_camera_to_player()
        self.zone_banner, self.zone_banner_t = z['name'], 3.0
        self.gate_prompt = ""

    def _difficulty(self):
        p = self.player
        return p.ng_plus if p else 0

    def _elite_roll(self, tx):
        """Probabilidad de élite según profundidad de zona + NG+."""
        if tx < 26:
            base = 0.05
        elif tx < 46:
            base = 0.10
        elif tx < 63:
            base = 0.15
        else:
            base = 0.20
        if random.random() < min(0.45, base + 0.05 * self._difficulty()):
            return random.choice(ELITE_AFFIXES)
        return None

    def _spawn_enemies(self, spawns):
        scale = self._difficulty()
        for etype, tx in spawns:
            e = Enemy(etype, tx * TILE_SIZE, TILE_SIZE * 10, scale=scale,
                      elite=self._elite_roll(tx))
            self.enemies.add(e)
            self.all_sprites.add(e)
        for mid, tx in MINIBOSS_SPAWNS:
            e = Enemy(MINIBOSS_DEFS[mid]['base'], tx * TILE_SIZE, TILE_SIZE * 10,
                      scale=scale, miniboss=mid)
            self.enemies.add(e)
            self.all_sprites.add(e)

    def respawn(self):
        """R al morir: conserva todo el progreso, reaparece en el último checkpoint."""
        self.combat_visuals.accents.clear()
        p = self.player
        if p.respawn_point:
            p.rect.topleft = p.respawn_point
        else:
            p.rect.topleft = PLAYER_START_POS
        p.velocity.update(0, 0)
        p.health = p.max_health
        p.cleanse()
        p.invincible = True
        p.invincibility_timer = 2.0
        # Reponer enemigos y limpiar jefe/proyectiles (el jefe se reactiva al entrar)
        for e in list(self.enemies):
            self.enemies.remove(e)
            self.all_sprites.remove(e)
        self._spawn_enemies(ENEMY_SPAWNS)
        self.all_sprites.add(p)
        self._reset_combat_state()
        self.set_screen(GameScreen.GAMEPLAY)
        self.rebinding = None
        self._go_sound = False
        self.inv_message = "Has despertado en el santuario..."
        self.inv_message_t = 3.0
        z = self.game_map.get_zone_at(p.rect.centerx)
        self.current_zone = z['id']
        p.explored_zones.add(z['id'])
        self.map_selected_zone = z['id']
        self.snap_camera_to_player()

    def completed(self):
        return self.player is not None and len(self.player.boss_defeated_ids) >= TOTAL_BOSSES

    def start_ng_plus(self):
        """Reinicia el mundo con enemigos más duros. Conserva nivel/skills/equipo/oro."""
        self.combat_visuals.accents.clear()
        p = self.player
        p.ng_plus += 1
        p.opened_gates.clear()
        p.boss_defeated_ids.clear()
        p.miniboss_defeated_ids.clear()
        p.unlocked_checkpoints.clear()
        p.explored_zones = {'meadow'}
        p.explored_rooms = {'meadow_trail'}
        p.completed_routes = set()
        p.discovered_secrets.clear()
        p.opened_secret_chests.clear()
        p.respawn_point = None
        self.game_map.reset_gates()
        self.game_map.reset_secrets()
        p.rect.topleft = PLAYER_START_POS
        p.velocity.update(0, 0)
        p.health = p.max_health
        p.cleanse()
        p.invincible = True
        p.invincibility_timer = 2.0
        for e in list(self.enemies):
            self.enemies.remove(e)
            self.all_sprites.remove(e)
        self.all_sprites.add(p)
        self._spawn_enemies(ENEMY_SPAWNS)
        self.drops = []
        self.shop_stock = []
        self._reset_combat_state()
        self.set_screen(GameScreen.GAMEPLAY)
        self._go_sound = False
        z = self.game_map.get_zone_at(p.rect.centerx)
        self.current_zone = z['id']
        p.explored_zones.add(z['id'])
        self.map_selected_zone = z['id']
        self.snap_camera_to_player()
        self.zone_banner, self.zone_banner_t = "NG+%d: %s" % (p.ng_plus, z['name']), 4.0
        self.inv_message = f"NG+{p.ng_plus}: enemigos +60% vida, +35% daño, +50% XP/oro y mejor botín"
        self.inv_message_t = 5.0
        audio.play('victory', 0.7)

    def fast_travel(self, cp_id):
        """Viaja a un checkpoint desbloqueado. Bloqueado durante el jefe."""
        p = self.player
        if self.boss is not None:
            self.inv_message = "No puedes viajar durante el jefe"
            self.inv_message_t = 2.0
            return False
        if cp_id not in p.unlocked_checkpoints:
            return False
        pos = self.game_map.spawn_pos_for(cp_id)
        if pos is None:
            return False
        p.rect.topleft = pos
        p.velocity.update(0, 0)
        p.health = p.max_health
        p.respawn_point = pos
        p.cleanse()
        self.set_screen(GameScreen.GAMEPLAY)
        audio.play('travel')
        z = self.game_map.get_zone_at(p.rect.centerx)
        self.current_zone = z['id']
        p.explored_zones.add(z['id'])
        self.map_selected_zone = z['id']
        self.snap_camera_to_player()
        self.zone_banner, self.zone_banner_t = z['name'], 3.0
        self.inv_message = f"Viaje: {z['name']} (vida restaurada)"
        self.inv_message_t = 2.5
        return True

    def _reset_combat_state(self):
        self.reset_secret_challenge()
        self.active_room_encounter = None
        self.boss = None
        self.projectiles = pygame.sprite.Group()
        self.hazards = []
        self.ally_shots = pygame.sprite.Group()
        self.pending_meteors = []
        self.blizzards = []
        self.death_visuals = []
        self.orb_angle = 0.0
        self.boss_banner_t = 0.0
        self.boss_phase_t = 0.0
        self.boss_phase_text = ""
        self.victory_t = 0.0
        self.victory_text = ""
        self.boss_intro_t = 0.0
        self.boss_defeat_t = 0.0
        self.pending_boss_defeat = None
        self.boss_reward_altar = None

    def try_load_save(self):
        """L: continuar partida guardada (clase, stats, equipo, puertas)."""
        p = Player('warrior')
        if not p.load_game():
            self.inv_message = p.last_load_error or "No hay guardado"
            self.inv_message_t = 3.0
            return False
        self.player = p
        self.selected_class = p.character_class
        self.game_map.apply_opened(p.opened_gates)
        self.game_map.apply_discovered_secrets(p.discovered_secrets)
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.all_sprites.add(self.player)
        self._spawn_enemies(LOAD_SPAWNS)
        self.drops = []
        self.set_screen(GameScreen.GAMEPLAY)
        self.rebinding = None
        self._go_sound = False
        self._reset_combat_state()
        z = self.game_map.get_zone_at(self.player.rect.centerx)
        self.current_zone = z['id']
        self.player.explored_zones.add(z['id'])
        self.map_selected_zone = z['id']
        self.snap_camera_to_player()
        self.zone_banner, self.zone_banner_t = z['name'], 3.0
        if p.last_load_recovered:
            self.inv_message = "Guardado recuperado desde la copia de seguridad"
            self.inv_message_t = 4.0
        return True
