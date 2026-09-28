"""Reglas puras para variantes direccionales y perfiles de carga."""

CHARGE_THRESHOLD = 0.22

CHARGE_PROFILES = {
    'warrior': {'damage': 1.7, 'reach': 1.35, 'color': (255, 205, 90)},
    'rogue': {'damage': 1.45, 'reach': 1.45, 'color': (210, 115, 245)},
    'mage': {'damage': 1.8, 'speed': 500.0, 'radius': 10, 'pierce': 2,
             'color': (110, 205, 255), 'visual': 'arcane', 'element': 'electric'},
    'ranger': {'damage': 1.65, 'speed': 650.0, 'radius': 5, 'pierce': 3,
               'color': (190, 240, 130), 'visual': 'arrow', 'element': 'physical'},
    'kitsune': {'damage': 1.6, 'speed': 540.0, 'radius': 11, 'pierce': 1,
                'color': (255, 115, 190), 'visual': 'orb', 'element': 'fire'},
    'reaper': {'damage': 1.65, 'reach': 1.5, 'color': (80, 235, 220)},
}


def directional_move(move, variant, airborne=False):
    result = dict(move)
    if variant == 'up':
        result.update(pattern='sweep_high', arc=100, aim=-55)
        result['launch'] = max(300, result.get('launch', 0))
    elif variant == 'down':
        if airborne:
            result.update(pattern='downstrike', arc=100, downstrike=True)
        else:
            result.update(pattern='sweep_low', arc=115, aim=42)
    elif variant == 'dash':
        result.update(pattern='thrust', arc=46)
        result['reach'] *= 1.35
        result['damage'] *= 1.15
    return result


def charge_values(character_class, charge):
    profile = dict(CHARGE_PROFILES[character_class])
    power = max(0.0, min(1.0, float(charge)))
    profile['damage'] = 1.0 + (profile['damage'] - 1.0) * power
    if 'reach' in profile:
        profile['reach'] = 1.0 + (profile['reach'] - 1.0) * power
    return profile
