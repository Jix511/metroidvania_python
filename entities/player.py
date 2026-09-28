# player.py - Clase base del jugador con sistema de habilidades integrado

import pygame
from entities.base import CombatEntity
from constants import (GREEN, CHARACTER_CLASSES, TILE_SIZE, PLAYER_START_POS,
    GRAVITY, JUMP_STRENGTH, MAX_FALL_SPEED, ATTACK_COOLDOWN, INVINCIBLE_TIME)
from systems.skills import get_all_skills_for_class
from systems.status import StatusList
from systems import controls
from core.paths import PLAYER_SAVE_PATH
from systems.json_storage import (JsonStorageError, load_json_with_recovery,
    save_json_atomic)
from systems.save_schema import (CURRENT_SAVE_VERSION, is_player_save_candidate,
    migrate_player_save)
from systems.combo_data import COMBOS
from systems.run_stats import normalize_stats
from systems.movement import approach

DASH_SPEED = 560.0
DASH_TIME = 0.18
DASH_COOLDOWN = 0.9
TELEPORT_DIST = TILE_SIZE * 4
TELEPORT_COOLDOWN = 1.2

class Player(CombatEntity):
    def __init__(self, character_class='warrior'):
        super().__init__()
        
        # --- Stats base por clase ---
        self.character_class = character_class
        if character_class in CHARACTER_CLASSES:
            char_data = CHARACTER_CLASSES[character_class]
            self.base_health = char_data['health']
            self.base_speed = char_data['speed']
            self.base_damage = char_data['damage']
            self.name = char_data['name']
            self.description = char_data['description']
            self.starting_ability = char_data['starting_ability']
        else:
            self.base_health = 100
            self.base_speed = 170.0
            self.base_damage = 10
            self.name = 'Guerrero'
            self.description = 'Fuerte en combate, pero lento'
            self.starting_ability = 'golpe_cargado'
        
        # Stats actuales (base + bonuses de skills/equipamiento)
        self.max_health = self.base_health
        self.health = self.max_health
        self.speed = self.base_speed
        self.damage = self.base_damage
        
        # --- Sistema de Habilidades / Skill Tree ---
        self.skill_points = 0
        self.skill_ranks = {}  # {skill_id: rank}
        self.unlocked_abilities = set()  # Habilidades mecánicas desbloqueadas
        self.available_skills = get_all_skills_for_class(character_class)

        # --- Equipamiento / Inventario ---
        from systems.items import SLOTS
        self.equipment = {s: None for s in SLOTS}
        self.inventory = []  # lista de item dicts
        self.gold = 0
        # Pociones
        from systems.items import POTION_MAX
        self.potions = 1  # empezar con 1 para descubrir la mecánica
        self.potion_cd = 0.0
        self.opened_gates = set()
        self.boss_defeated_ids = set()
        self.unlocked_checkpoints = set()
        self.explored_zones = {'meadow'}
        self.explored_rooms = {'meadow_trail'}
        self.completed_encounters = set()
        self.completed_routes = set()
        self.respawn_point = None  # (x, y) px o None = spawn inicial
        self.ng_plus = 0  # ciclo NG+ (0 = primera partida)
        self.miniboss_defeated_ids = set()
        self.bestiary = {}  # id entrada -> kills
        self.quest_states = {}
        self.collected_items = set()
        self.discovered_secrets = set()
        self.opened_secret_chests = set()
        self.statistics = normalize_stats()
        self.unlocked_achievements = set()
        self.status = StatusList()
        self._dot_carry = 0.0
        self.spell_cd = {}  # hechizo -> segundos restantes (transitorio)
        self.slow_factor = 1.0  # juego lo pone a 0.5 mientras carga ataque
        self.spin_t = 0.0  # giro del torbellino (visual)
        self.souls = 0  # recurso exclusivo de la Segadora
        self.dash_trail = (120, 220, 255)
        # Mecánicas de movimiento (cooldowns en segundos)
        self.dash_cooldown = 0.0
        self.dash_time = 0.0
        self.dash_dir = 1
        self.teleport_cooldown = 0.0
        self.touching_wall = False
        self.wall_dir = 0
        
        # Desbloquear ability inicial de la clase
        self.unlocked_abilities.add(self.starting_ability)
        
        # Multiplicadores dinámicos (se recalculan)
        self._stat_multipliers = {
            'damage': 1.0,
            'speed': 1.0,
            'max_health': 1.0,
            'damage_taken': 1.0,
            'crit_chance': 0.0,
            'crit_damage': 1.5,
            'evasion': 0.0,
            'xp_gain': 1.0,
            'gold_find': 1.0,
            'fire_damage': 1.0,
            'ice_slow': 1.0,
        }
        
        # Rectángulo del jugador
        self.width = TILE_SIZE
        self.height = TILE_SIZE
        self.image = pygame.Surface((self.width, self.height))
        self.image.fill(GREEN)
        
        # Posición
        self.rect = self.image.get_rect()
        self.rect.topleft = PLAYER_START_POS
        
        # Movimiento
        self.velocity = pygame.math.Vector2(0, 0)
        self.on_ground = False
        self.coyote = 0.0  # gracia tras salir de un borde (s)
        self.jump_buf = 0.0  # salto memorizado al pulsar antes (s)
        self._jump_held = False
        self.movement_lock_t = 0.0
        
        # Combate
        self.attack_cooldown = 0
        self.action_anim_t = 0.0
        self.action_anim_duration = 0.0
        self.facing_right = True
        self.combo_step = 0
        self.combo_mode = None
        self.combo_timer = 0.0
        self.parry_window = 0.0
        self.parry_cooldown = 0.0
        self.counter_bonus_t = 0.0
        
        # Invencibilidad
        self.invincible = False
        self.invincibility_timer = 0
        self.hit_flash = 0.0
        
        # Experiencia
        self.experience = 0
        self.level = 1
        self.xp_to_next_level = 100
        
        # UI Skill Tree
        self.skill_tree_selected_category = 'combat'
        self.skill_tree_selected_skill = None
        self.skill_categories = ['combat', 'defense', 'movement', 'utility']
    
    # =========================================================================
    # RECÁLCULO DE STATS
    # =========================================================================
    
    def recalculate_stats(self):
        """Recalcula todos los stats desde base + skills + equipamiento"""
        # Reset a base
        self.max_health = self.base_health
        self.speed = self.base_speed
        self.damage = self.base_damage
        self._stat_multipliers = {
            'damage': 1.0, 'speed': 1.0, 'max_health': 1.0,
            'damage_taken': 1.0, 'crit_chance': 0.0, 'crit_damage': 1.5,
            'evasion': 0.0, 'xp_gain': 1.0, 'gold_find': 1.0,
            'fire_damage': 1.0, 'ice_slow': 1.0,
        }
        self.unlocked_abilities = {self.starting_ability}

        # Equipo: bonus planos y aditivos primero
        _equip_flat_dmg = 0
        _equip_flat_hp = 0
        _equip_flat_speed = 0.0
        for item in self.equipment.values():
            if not item:
                continue
            st = item.get('stats', {})
            _equip_flat_dmg += int(st.get('damage', 0))
            _equip_flat_hp += int(st.get('max_health', 0))
            _equip_flat_speed += float(st.get('speed', 0))
            for k in ('crit_chance', 'evasion', 'crit_damage'):
                self._stat_multipliers[k] += float(st.get(k, 0.0))
            for k in ('xp_gain', 'gold_find', 'fire_damage'):
                self._stat_multipliers[k] += float(st.get(k, 0.0))
            if 'damage_taken' in st:
                self._stat_multipliers['damage_taken'] *= float(st['damage_taken'])
        
        # Aplicar todos los skills comprados
        for skill_id, rank in self.skill_ranks.items():
            if rank > 0:
                skill = self.available_skills.get(skill_id)
                if skill:
                    self._apply_skill_rank(skill, rank)
        
        # Aplicar multiplicadores finales + equipo plano
        self.damage = int(self.damage * self._stat_multipliers['damage']) + _equip_flat_dmg
        self.speed = self.speed * self._stat_multipliers['speed'] + _equip_flat_speed
        self.max_health = int(self.max_health * self._stat_multipliers['max_health']) + _equip_flat_hp
        # Topes anti-rotura: esquiva máx 60%, crítico máx 80%
        self._stat_multipliers['evasion'] = min(0.6, self._stat_multipliers['evasion'])
        self._stat_multipliers['crit_chance'] = min(0.8, self._stat_multipliers['crit_chance'])
        self.health = min(self.health, self.max_health)
        self.souls = min(self.souls, self.soul_limit())
        if self.health <= 0 and self.max_health > 0:
            self.health = min(self.max_health, max(1, self.health))

    # --- Equipamiento ---
    def add_item(self, item):
        self.inventory.append(item)
        name = item.get('name') if isinstance(item, dict) else None
        if name:
            self.collected_items.add(name)
        return True

    def equip_item(self, item_id):
        for i, it in enumerate(self.inventory):
            if it.get('id') == item_id:
                slot = it.get('slot')
                if slot not in self.equipment:
                    return False, "Slot inválido"
                old = self.equipment[slot]
                self.equipment[slot] = it
                del self.inventory[i]
                if old:
                    self.inventory.append(old)
                self.recalculate_stats()
                return True, f"Equipado: {it.get('name')}"
        return False, "Item no está en inventario"

    def unequip_slot(self, slot):
        if slot not in self.equipment:
            return False, "Slot inválido"
        it = self.equipment[slot]
        if not it:
            return False, "Slot vacío"
        self.equipment[slot] = None
        self.inventory.append(it)
        self.recalculate_stats()
        return True, f"Desequipado: {it.get('name')}"

    def add_gold(self, amount):
        mult = self._stat_multipliers.get('gold_find', 1.0)
        # gold_find en equipo es aditivo sobre 1.0 (0.12=+12%)
        gained = int(round(amount * mult))
        self.gold += gained
        self.stat_add('gold_earned', gained)
        return gained

    def stat_add(self, key, amount=1):
        if key in self.statistics:
            self.statistics[key] += amount

    def stat_max(self, key, value):
        if key in self.statistics:
            self.statistics[key] = max(self.statistics[key], value)

    def soul_limit(self):
        from systems.souls import soul_limit
        return soul_limit('soul_reservoir' in self.unlocked_abilities)

    def gain_souls(self, amount):
        """Carga la reserva de la Segadora y devuelve la cantidad obtenida."""
        if self.character_class != 'reaper' or amount <= 0:
            return 0
        from systems.souls import gain_souls
        self.souls, gained = gain_souls(
            self.souls, amount, 'soul_reservoir' in self.unlocked_abilities)
        if gained and 'soul_siphon' in self.unlocked_abilities:
            self.health = min(self.max_health, self.health + max(1, gained // 6))
        return gained

    def spend_gold(self, amount):
        if self.gold < amount:
            return False
        self.gold -= int(amount)
        return True

    def buy_potion(self):
        from systems.items import POTION_PRICE, POTION_MAX
        if self.potions >= POTION_MAX:
            return False, f"Cinturón lleno ({POTION_MAX})"
        if not self.spend_gold(POTION_PRICE):
            return False, f"Oro insuficiente ({POTION_PRICE}g)"
        self.potions += 1
        return True, f"Poción comprada ({self.potions}/{POTION_MAX})"

    def drink_potion(self):
        from systems.items import POTION_HEAL_FRAC
        if self.potion_cd > 0 or self.potions <= 0:
            return False
        if self.health >= self.max_health:
            return False
        self.potions -= 1
        self.stat_add('potions_used')
        self.health = min(self.max_health, self.health + int(self.max_health * POTION_HEAL_FRAC))
        self.potion_cd = 1.0
        return True
    
    def _apply_skill_rank(self, skill, rank):
        """Aplica los efectos de un rango específico de skill"""
        effects = skill.get('effects', {})
        
        # Stats planos (se suman por rango)
        if 'health' in effects:
            self.max_health += effects['health'] * rank
        
        # Multiplicadores (compuestos)
        if 'stat_multiplier' in effects:
            for stat, multiplier in effects['stat_multiplier'].items():
                if stat in self._stat_multipliers:
                    if stat in ['crit_chance', 'evasion']:  # Aditivos
                        self._stat_multipliers[stat] += (multiplier - 1.0) * rank
                    else:  # Multiplicativos
                        self._stat_multipliers[stat] *= (multiplier ** rank)
        
        # Nuevas habilidades mecánicas (solo al rank 1+)
        if 'new_ability' in effects and effects['new_ability'] and rank > 0:
            self.unlocked_abilities.add(effects['new_ability'])
    
    # =========================================================================
    # SISTEMA DE HABILIDADES - COMPRA/RESPEC
    # =========================================================================
    
    def can_buy_skill(self, skill_id):
        """Verifica si se puede comprar/mejorar una habilidad"""
        skill = self.available_skills.get(skill_id)
        if not skill:
            return False, "Habilidad no disponible para tu clase"
        
        current_rank = self.skill_ranks.get(skill_id, 0)
        if current_rank >= skill['max_rank']:
            return False, "Ya está al nivel máximo"
        
        if self.skill_points < skill['cost']:
            return False, f"Necesitas {skill['cost']} puntos (tienes {self.skill_points})"
        
        # Verificar prerequisitos
        for req_id in skill['requires']:
            req_skill = self.available_skills.get(req_id)
            req_rank = self.skill_ranks.get(req_id, 0)
            if not req_skill or req_rank < req_skill['max_rank']:
                req_name = req_skill['name'] if req_skill else req_id
                return False, f"Requiere: {req_name} (máx)"
        
        return True, "OK"
    
    def buy_skill(self, skill_id):
        """Compra/mejora una habilidad"""
        can_buy, msg = self.can_buy_skill(skill_id)
        if not can_buy:
            return False, msg
        
        skill = self.available_skills[skill_id]
        cost = skill['cost']
        
        self.skill_points -= cost
        self.skill_ranks[skill_id] = self.skill_ranks.get(skill_id, 0) + 1
        
        # Recalcular stats
        self.recalculate_stats()
        
        return True, f"¡{skill['name']} mejorado a rango {self.skill_ranks[skill_id]}!"
    
    def respec_all_skills(self):
        """Reinicia todas las habilidades y devuelve los puntos"""
        total_refund = 0
        for skill_id, rank in self.skill_ranks.items():
            skill = self.available_skills.get(skill_id)
            if skill:
                total_refund += skill['cost'] * rank
        self.skill_points += total_refund
        self.skill_ranks = {}
        self.recalculate_stats()
        return total_refund
    
    # =========================================================================
    # EXPERIENCIA Y NIVEL
    # =========================================================================
    
    def gain_experience(self, amount):
        """Añade experiencia con multiplicador"""
        amount = int(amount * self._stat_multipliers.get('xp_gain', 1.0))
        self.experience += amount
        self.stat_add('xp_earned', amount)
        
        while self.experience >= self.xp_to_next_level:
            self.level_up()
    
    def level_up(self):
        self.level += 1
        self.experience -= self.xp_to_next_level
        self.skill_points += 3
        self.xp_to_next_level = int(self.xp_to_next_level * 1.4)
        # Auto-curar al subir nivel
        self.health = self.max_health
        print(f"Nivel {self.level}! +3 pts habilidad. Vida restaurada.")
    
    # =========================================================================
    # COMBATE
    # =========================================================================
    
    def next_combo_move(self):
        mode = 'ground' if self.on_ground else 'air'
        chain = COMBOS[self.character_class][mode]
        if self.combo_timer <= 0 or self.combo_mode != mode:
            self.combo_step = 0
        else:
            self.combo_step = (self.combo_step + 1) % len(chain)
        self.combo_mode = mode
        self.combo_timer = 0.85
        return dict(chain[self.combo_step])

    def attack(self, enemies, range_mult=1.0, cooldown=ATTACK_COOLDOWN,
               downstrike=False, move=None):
        """Realiza ataque básico. Cooldown en segundos."""
        if self.attack_cooldown > 0:
            return []

        self.attack_cooldown = cooldown
        self.begin_action(cooldown)

        # Cada movimiento usa un arco que sigue la trayectoria visible del arma.
        class_reach = {'warrior': 1.85, 'rogue': 1.35,
                       'reaper': 2.0}.get(self.character_class, 1.5)
        attack_range = TILE_SIZE * class_reach * range_mult
        move = move or {}
        pattern = move.get('pattern', 'sweep')
        arc = float(move.get('arc', 125.0))
        aim = float(move.get('aim', 0.0))
        if pattern == 'spin':
            arc = 360.0
        elif pattern == 'thrust':
            arc = min(arc, 48.0)
        from systems.combat_geometry import arc_intersects_rect
        if downstrike:
            origin = (self.rect.centerx, self.rect.bottom - 2)
            return [enemy for enemy in enemies
                    if arc_intersects_rect(
                        origin,
                        (enemy.rect.x, enemy.rect.y,
                         enemy.rect.width, enemy.rect.height),
                        1, attack_range + TILE_SIZE, arc, 90.0)]

        facing = 1 if self.facing_right else -1
        origin = (self.rect.centerx, self.rect.centery + float(move.get('origin_y', 0)))
        hit_enemies = []
        for enemy in enemies:
            rect = enemy.rect
            if arc_intersects_rect(origin, (rect.x, rect.y, rect.width, rect.height),
                                   facing, attack_range, arc, aim):
                hit_enemies.append(enemy)
        
        return hit_enemies

    def begin_action(self, duration):
        self.action_anim_t = max(self.action_anim_t, float(duration))
        self.action_anim_duration = max(0.01, float(duration))

    def weapon_origin(self, target_x=None, target_y=None):
        """World-space origin matching the visible weapon instead of the hitbox center."""
        if target_x is not None:
            self.facing_right = target_x >= self.rect.centerx
        direction = 1 if self.facing_right else -1
        offsets = {
            'warrior': (18, -7), 'rogue': (16, -5),
            'mage': (17, -13), 'ranger': (19, -9),
            'kitsune': (18, -11),
            'reaper': (24, -9),
        }
        forward, vertical = offsets.get(self.character_class, (14, -6))
        return self.rect.centerx + direction * forward, self.rect.centery + vertical
    
    def take_damage(self, amount):
        """Recibe daño. Retorna (died: bool, msg: str)."""
        import random
        # Evasión
        if random.random() < self._stat_multipliers.get('evasion', 0):
            return False, "Esquivado"
        
        if self.invincible:
            return False, "Invencible"

        # Reducción de daño
        reduction = self._stat_multipliers.get('damage_taken', 1.0)
        final_damage = max(1, int(amount * reduction))
        
        # Mana shield (si tiene) - por ahora solo reduce, sin maná real
        if 'mana_shield' in self.unlocked_abilities:
            final_damage = max(1, int(final_damage * 0.7))
        
        self.health -= final_damage
        self.hit_flash = 0.12
        self.invincible = True
        self.invincibility_timer = INVINCIBLE_TIME
        
        if self.health <= 0:
            # Last stand check
            if 'last_stand' in self.unlocked_abilities:
                self.health = 1
                self.unlocked_abilities.discard('last_stand')  # Se gasta
                return False, "Ultima Voluntad activada"
            self.health = 0
            return True, "Muerto"
        return False, f"Dano: {final_damage}"
    
    # =========================================================================
    # GUARDADO/CARGA
    # =========================================================================
    
    def save_game(self):
        save_data = {
            'health': self.health,
            'max_health': self.max_health,
            'speed': self.speed,
            'damage': self.damage,
            'level': self.level,
            'experience': self.experience,
            'xp_to_next_level': self.xp_to_next_level,
            'skill_points': self.skill_points,
            'skill_ranks': self.skill_ranks,
            'souls': self.souls,
            'character_class': self.character_class,
            'position': list(self.rect.topleft),
            'base_health': self.base_health,
            'base_speed': self.base_speed,
            'base_damage': self.base_damage,
            'equipment': self.equipment,
            'inventory': self.inventory,
            'gold': self.gold,
            'opened_gates': sorted(self.opened_gates),
            'boss_defeated_ids': sorted(self.boss_defeated_ids),
            'unlocked_checkpoints': sorted(self.unlocked_checkpoints),
            'explored_zones': sorted(self.explored_zones),
            'explored_rooms': sorted(self.explored_rooms),
            'completed_encounters': sorted(self.completed_encounters),
            'completed_routes': sorted(self.completed_routes),
            'respawn_point': list(self.respawn_point) if self.respawn_point else None,
            'potions': self.potions,
            'ng_plus': self.ng_plus,
            'miniboss_defeated_ids': sorted(self.miniboss_defeated_ids),
            'bestiary': self.bestiary,
            'quest_states': self.quest_states,
            'collected_items': sorted(self.collected_items),
            'discovered_secrets': sorted(self.discovered_secrets),
            'opened_secret_chests': sorted(self.opened_secret_chests),
            'statistics': self.statistics,
            'unlocked_achievements': sorted(self.unlocked_achievements),
            'save_version': CURRENT_SAVE_VERSION,
        }

        try:
            save_json_atomic(PLAYER_SAVE_PATH, save_data, is_player_save_candidate)
            self.last_save_error = ''
            return True
        except (OSError, TypeError, ValueError, JsonStorageError) as exc:
            self.last_save_error = str(exc)
            return False
    
    def load_game(self):
        self.last_load_error = ''
        self.last_load_recovered = False
        try:
            save_data, recovered = load_json_with_recovery(
                PLAYER_SAVE_PATH, is_player_save_candidate)
            save_data = migrate_player_save(save_data)
        except FileNotFoundError:
            self.last_load_error = 'No hay una partida guardada'
            return False
        except (OSError, TypeError, ValueError, JsonStorageError) as exc:
            self.last_load_error = f'Guardado corrupto sin copia recuperable: {exc}'
            return False

        self.last_load_recovered = recovered
        
        # Restaurar base stats (migración saves viejos: speed<20 era px/frame)
        self.base_health = save_data.get('base_health', self.base_health)
        self.base_speed = save_data.get('base_speed', self.base_speed)
        self.base_damage = save_data.get('base_damage', self.base_damage)
        if self.base_speed < 20:
            self.base_speed *= 60.0
        _saved_speed = save_data.get('speed', self.base_speed)
        if _saved_speed < 20:
            _saved_speed *= 60.0
        
        # Restaurar estado
        self.health = save_data.get('health', self.base_health)
        self.max_health = save_data.get('max_health', self.base_health)
        self.speed = _saved_speed
        self.damage = save_data.get('damage', self.base_damage)
        self.level = save_data.get('level', 1)
        self.experience = save_data.get('experience', 0)
        self.xp_to_next_level = save_data.get('xp_to_next_level', 100)
        self.skill_points = save_data.get('skill_points', 0)
        self.skill_ranks = save_data.get('skill_ranks', {})
        self.souls = max(0, int(save_data.get('souls', 0)))
        self.character_class = save_data.get('character_class', 'warrior')
        # Equipo / inventario / oro
        from systems.items import SLOTS
        _eq = save_data.get('equipment', {})
        self.equipment = {s: _eq.get(s) for s in SLOTS}
        self.inventory = save_data.get('inventory', [])
        self.gold = save_data.get('gold', 0)
        self.opened_gates = set(save_data.get('opened_gates', []))
        self.boss_defeated_ids = set(save_data.get('boss_defeated_ids', []))
        self.unlocked_checkpoints = set(save_data.get('unlocked_checkpoints', []))
        self.explored_zones = set(save_data.get('explored_zones', ['meadow']))
        self.explored_rooms = set(save_data.get('explored_rooms', ['meadow_trail']))
        self.completed_encounters = set(save_data.get('completed_encounters', []))
        self.completed_routes = set(save_data.get('completed_routes', []))
        _rp = save_data.get('respawn_point')
        self.respawn_point = tuple(_rp) if _rp else None
        self.potions = int(save_data.get('potions', 1))
        self.potion_cd = 0.0
        self.ng_plus = int(save_data.get('ng_plus', 0))
        self.miniboss_defeated_ids = set(save_data.get('miniboss_defeated_ids', []))
        self.bestiary = dict(save_data.get('bestiary', {}))
        self.quest_states = dict(save_data.get('quest_states', {}))
        self.collected_items = set(save_data.get('collected_items', []))
        self.discovered_secrets = set(save_data.get('discovered_secrets', []))
        self.opened_secret_chests = set(save_data.get('opened_secret_chests', []))
        self.statistics = normalize_stats(save_data.get('statistics'))
        self.unlocked_achievements = set(save_data.get('unlocked_achievements', []))
        self.collected_items.update(
            item.get('name') for item in self.inventory
            if isinstance(item, dict) and item.get('name'))
        self.collected_items.update(
            item.get('name') for item in self.equipment.values()
            if isinstance(item, dict) and item.get('name'))
        
        # Actualizar starting_ability según la clase cargada
        if self.character_class in CHARACTER_CLASSES:
            self.starting_ability = CHARACTER_CLASSES[self.character_class]['starting_ability']
            self.name = CHARACTER_CLASSES[self.character_class]['name']
            self.description = CHARACTER_CLASSES[self.character_class]['description']
        
        # Recalcular todo
        self.available_skills = get_all_skills_for_class(self.character_class)
        self.recalculate_stats()
        
        # Posición
        x, y = save_data.get('position', PLAYER_START_POS)
        self.rect.topleft = (x, y)
        return True
    
    # =========================================================================
    # UPDATE
    # =========================================================================
    
    def _unembed(self, tilemap):
        """Garantía: si quedamos dentro de un sólido, salir hacia arriba."""
        abilities = set(self.unlocked_abilities)
        if self.dash_time > 0:
            abilities.add('dash_active')
        if tilemap is not None and tilemap.check_collision(self.rect, abilities):
            for _ in range(48):
                self.rect.y -= 1
                if not tilemap.check_collision(self.rect, abilities):
                    break
            self.velocity.y = min(self.velocity.y, 0)

    def _move_with_collision(self, tilemap, dt):
        abil = set(self.unlocked_abilities)
        if self.dash_time > 0:
            abil.add('dash_active')
        if tilemap is None:
            self.rect.x += int(self.velocity.x * dt)
            self.rect.y += int(self.velocity.y * dt)
            self.on_ground = False
            self.touching_wall = False
            return
        dx = self.velocity.x * dt
        steps_x = max(1, int(abs(dx) // 8 + 1))
        self.touching_wall = False
        self.wall_dir = 0
        for _ in range(steps_x):
            old_x = self.rect.x
            self.rect.x += int(round(dx / steps_x))
            if tilemap.check_collision(self.rect, abil):
                self.rect.x = old_x
                self.touching_wall = True
                self.wall_dir = 1 if dx > 0 else -1
                self.velocity.x = 0
                break
        dy = self.velocity.y * dt
        steps_y = max(1, int(abs(dy) // 8 + 1))
        landed = False
        for _ in range(steps_y):
            self.rect.y += int(round(dy / steps_y))
            if tilemap.check_collision(self.rect, abil):
                if self.velocity.y > 0:
                    landed = True
                    self.rect.bottom = (self.rect.bottom // TILE_SIZE) * TILE_SIZE
                    if hasattr(self, '_double_jumped'):
                        self._double_jumped = False
                elif self.velocity.y < 0:
                    self.rect.top = ((self.rect.top // TILE_SIZE) + 1) * TILE_SIZE
                self.velocity.y = 0
                break
        if landed:
            self.on_ground = True
        else:
            probe = self.rect.move(0, 1)
            if not tilemap.check_collision(probe, abil):
                self.on_ground = False

    def try_poison(self, duration=4.0):
        """Aplica veneno salvo inmunidad. Retorna 'immune'/'applied'."""
        if 'poison_immunity' in self.unlocked_abilities:
            return 'immune'
        self.status.apply('poison', duration)
        return 'applied'

    def record_kill(self, entry_key):
        self.bestiary[entry_key] = self.bestiary.get(entry_key, 0) + 1
        return self.bestiary[entry_key] == 1  # True si es descubrimiento

    def cleanse(self):
        """Limpia estados y textos pendientes (respawn/viaje/NG+)."""
        self.status = StatusList()
        self.fx_texts = []
        self.invincible = False
        self.invincibility_timer = 0

    def update(self, dt, tilemap=None, enemies=None):
        dt = min(dt, 1.0 / 20.0)
        self.anim_t += dt
        if self.hit_flash > 0:
            self.hit_flash -= dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo_step = 0
                self.combo_mode = None
        if self.action_anim_t > 0:
            self.action_anim_t -= dt
        if self.invincible:
            self.invincibility_timer -= dt
            if self.invincibility_timer <= 0:
                self.invincible = False
        if self.dash_cooldown > 0:
            self.dash_cooldown -= dt
        if self.teleport_cooldown > 0:
            self.teleport_cooldown -= dt
        if self.potion_cd > 0:
            self.potion_cd -= dt
        if self.spin_t > 0:
            self.spin_t -= dt
        self.parry_window = max(0.0, self.parry_window - dt)
        self.parry_cooldown = max(0.0, self.parry_cooldown - dt)
        self.counter_bonus_t = max(0.0, self.counter_bonus_t - dt)
        if self.movement_lock_t > 0:
            self.movement_lock_t -= dt
        for sid in list(self.spell_cd.keys()):
            self.spell_cd[sid] -= dt
            if self.spell_cd[sid] <= 0:
                del self.spell_cd[sid]

        # DoT de estados (ignora iframes). Retorna True si mata.
        dot = self.status.update(dt)
        if dot > 0:
            self.health -= dot
            self._dot_carry += dot
            whole = int(self._dot_carry)
            if whole >= 1:
                self._dot_carry -= whole
                self.queue_fx_text(whole, (120, 220, 120))
            if self.health <= 0:
                self.health = 0
                if 'last_stand' in self.unlocked_abilities:
                    self.health = 1
                    self.unlocked_abilities.discard('last_stand')
                else:
                    return True

        # Dash/rodadura: movimiento horizontal fijo, ignora input
        if self.dash_time > 0:
            self.dash_time -= dt
            self.velocity.x = self.dash_dir * getattr(self, '_dash_speed', DASH_SPEED)
            self.velocity.y = min(self.velocity.y, 120.0)
            self.invincible = True
            self.invincibility_timer = max(self.invincibility_timer, 0.05)
            self._move_with_collision(tilemap, dt)
            self._unembed(tilemap)
            return bool(self.health <= 0)

        # Input movimiento (speed en px/s, reducido por slow y carga)
        stunned = self.status.stunned()
        spd = self.speed * self.status.speed_mult() * self.slow_factor
        move_axis = 0
        if stunned and self.movement_lock_t <= 0:
            self.velocity.x = approach(self.velocity.x, 0.0, 2200.0 * dt)
        if not stunned and self.movement_lock_t <= 0:
            if controls.held('left'):
                move_axis -= 1
                self.facing_right = False
            if controls.held('right'):
                move_axis += 1
                self.facing_right = True
            target_x = move_axis * spd
            acceleration = 2100.0 if self.on_ground else 1250.0
            if move_axis == 0:
                acceleration = 2700.0 if self.on_ground else 850.0
            self.velocity.x = approach(self.velocity.x, target_x, acceleration * dt)
            # Buffer: memoriza la pulsación; coyote: gracia tras el borde
            jr = controls.held('jump')
            released_jump = self._jump_held and not jr
            if jr and not self._jump_held:
                self.jump_buf = 0.12
            self._jump_held = jr
            if released_jump and self.velocity.y < -120:
                self.velocity.y *= 0.52
            if self.on_ground:
                self.coyote = 0.10
            else:
                self.coyote = max(0.0, self.coyote - dt)
            if self.jump_buf > 0:
                self.jump_buf -= dt
                if self.on_ground or self.coyote > 0:
                    self.velocity.y = JUMP_STRENGTH
                    self.on_ground = False
                    self.coyote = 0.0
                    self.jump_buf = 0.0

        # Wall jump con tecla de salto contra pared
        if controls.held('jump') and not stunned and not self.on_ground and self.touching_wall:
            self.try_wall_jump()

        # Gravedad (menor si agarrado a pared con wall_jump)
        grav = GRAVITY * (0.35 if (self.touching_wall and 'wall_jump' in self.unlocked_abilities and self.velocity.y > 0) else 1.0)
        self.velocity.y += grav * dt
        if self.velocity.y > MAX_FALL_SPEED:
            self.velocity.y = MAX_FALL_SPEED

        self._move_with_collision(tilemap, dt)
        self._unembed(tilemap)

    def try_double_jump(self):
        if 'double_jump' in self.unlocked_abilities and not self.on_ground:
            if not getattr(self, '_double_jumped', False):
                self.velocity.y = JUMP_STRENGTH
                self._double_jumped = True
                return True
        return False

    def try_dash(self):
        """Ejecuta la técnica de evasión propia de la clase."""
        if 'spirit_step' in self.unlocked_abilities:
            speed, time, cd, trail = 620.0, 0.16, 0.75, (255, 125, 190)
        elif 'dash' in self.unlocked_abilities:
            speed, time, cd, trail = DASH_SPEED, DASH_TIME, DASH_COOLDOWN, (120, 220, 255)
        elif 'dodge_roll' in self.unlocked_abilities:
            speed, time, cd, trail = 380.0, 0.25, 1.0, (170, 170, 190)
        else:
            return False
        if self.dash_cooldown > 0:
            return False
        if self.action_anim_t > 0:
            self.action_anim_t = 0.0
            self.attack_cooldown = 0.0
            self.combo_timer = max(self.combo_timer, 0.85)
        if controls.held('left'):
            self.dash_dir = -1
            self.facing_right = False
        elif controls.held('right'):
            self.dash_dir = 1
            self.facing_right = True
        else:
            self.dash_dir = 1 if self.facing_right else -1
        self.dash_time = time
        self.dash_cooldown = cd
        self.dash_trail = trail
        # Guardar params del dash activo para update()
        self._dash_speed = speed
        return True

    def begin_parry(self):
        if self.parry_cooldown > 0 or self.dash_time > 0:
            return False
        windows = {'warrior': 0.18, 'rogue': 0.13, 'ranger': 0.14,
                   'mage': 0.16, 'kitsune': 0.15, 'reaper': 0.15}
        self.parry_window = windows.get(self.character_class, 0.14)
        self.parry_cooldown = 0.9
        self.begin_action(0.24)
        return True

    def try_backflip(self):
        """Voltereta del arquero: salto atrás. El juego dispara la flecha."""
        if 'backflip' not in self.unlocked_abilities:
            return False
        if self.spell_cd.get('backflip', 0) > 0 or not self.on_ground:
            return False
        self.spell_cd['backflip'] = 3.0
        back = -1 if self.facing_right else 1
        self.velocity.x = back * 300.0
        self.velocity.y = JUMP_STRENGTH * 0.7
        self.on_ground = False
        self.invincible = True
        self.invincibility_timer = max(self.invincibility_timer, 0.3)
        self.movement_lock_t = 0.18
        return True

    def try_wall_jump(self):
        if 'wall_jump' not in self.unlocked_abilities or self.on_ground or not self.touching_wall:
            return False
        self.velocity.y = JUMP_STRENGTH
        self.velocity.x = -self.wall_dir * self.speed * 1.1
        self.facing_right = self.velocity.x > 0
        self.on_ground = False
        # Aplicar empuje inmediato para despegar de la pared
        self.rect.x += int(-self.wall_dir * 3)
        self.movement_lock_t = 0.14
        return True

    def try_teleport(self, tilemap):
        if 'teleport' not in self.unlocked_abilities or self.teleport_cooldown > 0:
            return False
        direction = 1 if self.facing_right else -1
        target = self.rect.copy()
        moved = False
        for step in (TELEPORT_DIST, TELEPORT_DIST * 0.75, TELEPORT_DIST * 0.5, TELEPORT_DIST * 0.25):
            cand = self.rect.copy()
            cand.x += int(direction * step)
            abil = self.unlocked_abilities
            if tilemap is None or not tilemap.check_collision(cand, abil):
                target = cand
                moved = True
                break
        if not moved:
            return False
        self.rect = target
        self.velocity.y = min(self.velocity.y, 0)
        self.teleport_cooldown = TELEPORT_COOLDOWN
        self.invincible = True
        self.invincibility_timer = max(self.invincibility_timer, 0.15)
        return True
    
    # =========================================================================
    # UI SKILL TREE
    # =========================================================================
    
    def get_skills_by_category(self, category):
        return {k: v for k, v in self.available_skills.items() if v['category'] == category}
    
    def get_skill_tree_progress(self):
        """Retorna stats para mostrar en UI"""
        total_skills = len(self.available_skills)
        unlocked = sum(1 for r in self.skill_ranks.values() if r > 0)
        total_points_spent = sum(
            self.available_skills[sid]['cost'] * rank 
            for sid, rank in self.skill_ranks.items()
        )
        return {
            'total': total_skills,
            'unlocked': unlocked,
            'points_spent': total_points_spent,
            'points_available': self.skill_points,
        }
