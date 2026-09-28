# controls.py - Teclas reasignables con persistencia en saves/controls.json.

import pygame

from core.paths import CONTROLS_SAVE_PATH
from systems.json_storage import (JsonStorageError, load_json_with_recovery,
    save_json_atomic)

SAVE_PATH = CONTROLS_SAVE_PATH

DEFAULTS = {
    'left': ['a', 'left'],
    'right': ['d', 'right'],
    'jump': ['w', 'up'],
    'down': ['s', 'down'],
    'attack': ['space'],
    'dash': ['left shift', 'right shift'],
    'parry': ['z'],
    'teleport': ['e'],
    'potion': ['q'],
    'nova': ['v'],
    'meteor': ['g'],
    'blizzard': ['b'],
    'whirlwind': ['x'],
    'skills': ['k', 'tab'],
    'inventory': ['i'],
    'travel': ['m'],
    'map': ['h'],
    'journal': ['j'],
    'quests': ['u'],
    'shop': ['f'],
    'mute': ['n'],
    'ngplus': ['p'],
    'classes': ['c'],
    'confirm': ['r'],
}

ACTION_LABELS = {
    'left': 'Izquierda', 'right': 'Derecha', 'jump': 'Saltar', 'down': 'Abajo',
    'attack': 'Atacar/Cargar', 'dash': 'Dash/Rodada', 'parry': 'Parada',
    'teleport': 'Teleport',
    'potion': 'Poción', 'nova': 'Nova', 'meteor': 'Meteoritos',
    'blizzard': 'Ventisca', 'whirlwind': 'Torbellino', 'skills': 'Skills',
    'inventory': 'Equipo', 'travel': 'Viaje', 'map': 'Mapa',
    'journal': 'Bestiario', 'quests': 'Misiones', 'shop': 'Tienda',
    'mute': 'Sonido', 'ngplus': 'NG+', 'classes': 'Clases', 'confirm': 'Confirmar',
}

REBINDABLE = list(DEFAULTS.keys())

_bindings = {}  # action -> [keycodes]


def _valid_bindings(data):
    return (isinstance(data, dict)
            and all(isinstance(action, str) and isinstance(names, list)
                    and all(isinstance(name, str) for name in names)
                    for action, names in data.items()))


def _to_code(name):
    try:
        return pygame.key.key_code(name)
    except Exception:
        return None


def load():
    global _bindings
    data = {}
    try:
        data, _recovered = load_json_with_recovery(SAVE_PATH, _valid_bindings)
    except (FileNotFoundError, OSError, JsonStorageError):
        data = {}
    _bindings = {}
    for action, default_names in DEFAULTS.items():
        names = data.get(action, default_names)
        # Migración: el default viejo de dash ('shift') era inválido y solo
        # guardaba el derecho; restaurar ambos si es el caso.
        if action == 'dash' and names == ['right shift']:
            names = default_names
        codes = [c for c in (_to_code(n) for n in names) if c is not None]
        if not codes:  # nombre inválido o vacío: defaults (también validados)
            codes = [c for c in (_to_code(n) for n in default_names) if c is not None]
        _bindings[action] = codes
    return _bindings


def save():
    names = {}
    for action, codes in _bindings.items():
        names[action] = [pygame.key.name(c) for c in codes]
    try:
        save_json_atomic(SAVE_PATH, names, _valid_bindings)
        return True
    except (OSError, TypeError, ValueError, JsonStorageError):
        return False


def reset_defaults():
    global _bindings
    _bindings = {}
    for action, names in DEFAULTS.items():
        _bindings[action] = [c for c in (_to_code(n) for n in names) if c is not None]
    save()


def codes(action):
    return list(_bindings.get(action, []))


def held(action):
    """True si alguna tecla de la acción está pulsada ahora."""
    try:
        state = pygame.key.get_pressed()
    except Exception:
        return False
    return any(state[c] for c in _bindings.get(action, []) if c < len(state))


def key_in(action, keycode):
    return keycode in _bindings.get(action, [])


def actions_for(keycode):
    return [a for a, cs in _bindings.items() if keycode in cs]


def set_binding(action, keycode):
    """Asigna la tecla (la roba a otras acciones para evitar duplicados)."""
    if action not in _bindings:
        return False
    for a, cs in _bindings.items():
        if keycode in cs:
            cs.remove(keycode)
    _bindings[action] = [keycode]
    # No dejar acciones vacías (salvo que su única tecla fuera la robada):
    # rellenar con sus defaults excepto la tecla recién asignada.
    for a, cs in _bindings.items():
        if not cs:
            restored = [c for c in (_to_code(n) for n in DEFAULTS[a])
                        if c is not None and c != keycode]
            if restored:
                _bindings[a] = restored
    save()
    return True


def key_label(keycode):
    try:
        name = pygame.key.name(keycode)
    except Exception:
        name = '?'
    return {'left': '←', 'right': '→', 'up': '↑', 'down': '↓', 'space': 'Espacio',
            'tab': 'TAB', 'left shift': 'Shift', 'right shift': 'ShiftD'}.get(name, name.upper())


def action_label(action):
    return ACTION_LABELS.get(action, action)


load()
