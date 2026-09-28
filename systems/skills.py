# skills.py - Sistema de árbol de habilidades por clase

from systems.skill_data import (CLASS_SKILL_TREES, SKILL_CATEGORIES,
    UNIVERSAL_SKILLS)

# Todas las habilidades disponibles (clase + universales)
def get_all_skills_for_class(character_class):
    """Obtiene todas las habilidades disponibles para una clase"""
    skills = {}
    skills.update(UNIVERSAL_SKILLS)
    if character_class in CLASS_SKILL_TREES:
        skills.update(CLASS_SKILL_TREES[character_class])
    return skills

def get_skill_categories():
    """Obtiene las categorías de habilidades para organización UI"""
    return list(SKILL_CATEGORIES)

def get_skills_by_category(skills_dict, category):
    """Filtra habilidades por categoría"""
    return {k: v for k, v in skills_dict.items() if v['category'] == category}

# ============================================================================
# FUNCIONES DE UTILIDAD PARA EL SISTEMA
# ============================================================================

def can_afford_skill(player, skill_id, skills_dict):
    """Verifica si el jugador puede permitirse la habilidad"""
    skill = skills_dict.get(skill_id)
    if not skill:
        return False, "Habilidad no existe"
    
    current_rank = player.skill_ranks.get(skill_id, 0)
    if current_rank >= skill['max_rank']:
        return False, "Ya está al máximo"
    
    if player.skill_points < skill['cost']:
        return False, f"Puntos insuficientes (necesitas {skill['cost']})"
    
    # Verificar prerequisitos
    for req_id in skill['requires']:
        req_rank = player.skill_ranks.get(req_id, 0)
        req_skill = skills_dict.get(req_id)
        if not req_skill or req_rank < req_skill['max_rank']:
            req_name = req_skill['name'] if req_skill else req_id
            return False, f"Requiere: {req_name} (máximo)"
    
    return True, "OK"

def apply_skill_effects(player, skill, rank):
    """Aplica los efectos de una habilidad al jugador"""
    effects = skill.get('effects', {})
    
    # Stats planos
    if 'health' in effects:
        player.max_health += effects['health']
        player.health += effects['health']
    
    # Multiplicadores de stats
    if 'stat_multiplier' in effects:
        for stat, multiplier in effects['stat_multiplier'].items():
            if stat == 'damage':
                player.damage = int(player.damage * multiplier)
            elif stat == 'speed':
                player.speed *= multiplier
            elif stat == 'max_health':
                player.max_health = int(player.max_health * multiplier)
                player.health = int(player.health * multiplier)
            # Otros multiplicadores se guardan para uso en combate
            setattr(player, f'_mult_{stat}', multiplier)
    
    # Nuevas habilidades mecánicas
    if 'new_ability' in effects and effects['new_ability']:
        ability_name = effects['new_ability']
        player.unlocked_abilities.add(ability_name)
        print(f"¡Nueva habilidad desbloqueada: {ability_name}!")

def remove_skill_effects(player, skill, rank):
    """Revierte los efectos de una habilidad (para respec)"""
    effects = skill.get('effects', {})
    
    if 'health' in effects:
        player.max_health -= effects['health']
        player.health = min(player.health, player.max_health)
    
    # Nota: Los multiplicadores son más complejos de revertir exactamente
    # En un juego real se recalcularían todos los stats desde base
    
    if 'new_ability' in effects and effects['new_ability']:
        ability_name = effects['new_ability']
        player.unlocked_abilities.discard(ability_name)
