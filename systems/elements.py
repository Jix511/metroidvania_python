"""Elemental resistances and deterministic status reactions."""


ELEMENT_COLORS = {
    'physical': (235, 225, 205),
    'fire': (255, 115, 45),
    'ice': (130, 215, 255),
    'poison': (105, 225, 115),
    'electric': (255, 235, 95),
}

ENEMY_RESISTANCES = {
    'slime': {'poison': 0.55, 'electric': 1.25, 'ice': 1.15},
    'skeleton': {'poison': 0.7, 'physical': 0.85, 'fire': 1.25},
    'bat': {'electric': 1.2, 'ice': 0.85},
    'goblin': {'fire': 0.85, 'poison': 1.2},
    'moss_boar': {'poison': 0.7, 'fire': 1.2},
    'crystal_beetle': {'physical': 0.75, 'fire': 1.35, 'electric': 0.8},
    'ruin_drowned': {'poison': 0.65, 'electric': 1.3},
    'rune_acolyte': {'electric': 0.7, 'physical': 1.15},
    'storm_harpy': {'electric': 0.55, 'ice': 1.3},
}

BOSS_RESISTANCES = {
    'cavern_mother': {'poison': 0.35, 'fire': 1.3},
    'sanctum_guardian': {'physical': 0.8, 'electric': 1.25},
    'void_heart': {'ice': 0.5, 'fire': 0.8, 'electric': 1.2},
}


def damage_multiplier(target, element):
    if element not in ELEMENT_COLORS:
        return 1.0
    boss_id = getattr(target, 'boss_id', None)
    if boss_id:
        value = BOSS_RESISTANCES.get(boss_id, {}).get(element, 1.0)
        phase = getattr(target, 'phase', 1)
        return value * (0.9 if phase >= 3 and element == 'physical' else 1.0)
    enemy_type = getattr(target, 'enemy_type', None)
    return ENEMY_RESISTANCES.get(enemy_type, {}).get(element, 1.0)


def apply_element(status, element, duration=3.0, heavy=False):
    """Apply an element and return a reaction descriptor when combinations meet."""
    active = status.active
    reaction = None
    if element == 'fire' and 'poison' in active or element == 'poison' and 'burn' in active:
        status.remove('poison')
        status.remove('burn')
        reaction = {'id': 'toxic_blast', 'name': 'EXPLOSIÓN TÓXICA',
                    'damage': 18, 'radius': 72, 'color': (175, 255, 85)}
    elif element == 'fire' and ('chill' in active or 'slow' in active):
        status.remove('chill')
        status.remove('slow')
        reaction = {'id': 'thermal_shock', 'name': 'CHOQUE TÉRMICO',
                    'damage': 15, 'radius': 48, 'color': (235, 225, 255)}
    elif element == 'ice' and 'burn' in active:
        status.remove('burn')
        reaction = {'id': 'thermal_shock', 'name': 'CHOQUE TÉRMICO',
                    'damage': 15, 'radius': 48, 'color': (235, 225, 255)}
    elif element == 'electric' and ('chill' in active or 'slow' in active):
        reaction = {'id': 'chain_lightning', 'name': 'CADENA ELÉCTRICA',
                    'damage': 12, 'radius': 105, 'color': (255, 240, 95)}
    elif element == 'physical' and heavy and ('chill' in active or 'slow' in active):
        status.remove('chill')
        status.remove('slow')
        reaction = {'id': 'shatter', 'name': 'FRAGMENTADO',
                    'damage': 22, 'radius': 35, 'color': (165, 230, 255)}

    state_id = {'fire': 'burn', 'ice': 'chill', 'poison': 'poison',
                'electric': 'shock'}.get(element)
    if state_id:
        status.apply(state_id, duration)
    return reaction
