# sprites.py - Sprites procedurales animados. Sin assets externos.
# Cada constructor devuelve {'idle': [...], 'run': [...], 'jump': [...], 'attack': [...]}.

import pygame

SKIN = (235, 200, 160)
DARK = (20, 18, 26)


def _surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _r(s, x, y, w, h, c):
    s.fill(c, pygame.Rect(int(x), int(y), int(w), int(h)))


# ============================================================================
# JUGADOR (24x30, anclado por los pies)
# ============================================================================

_PLAYER_STYLE = {
    'warrior': {'torso': (70, 110, 180), 'legs': (45, 45, 60), 'trim': (200, 60, 60),
                'head': 'helmet', 'weapon': 'sword'},
    'rogue':   {'torso': (55, 90, 70), 'legs': (35, 40, 45), 'trim': (40, 40, 48),
                'head': 'hood', 'weapon': 'dagger'},
    'mage':    {'torso': (110, 60, 160), 'legs': (70, 40, 110), 'trim': (255, 220, 90),
                'head': 'hat', 'weapon': 'staff'},
    'ranger':  {'torso': (60, 130, 70), 'legs': (80, 60, 40), 'trim': (150, 110, 60),
                'head': 'hood', 'weapon': 'bow'},
    'kitsune': {'torso': (95, 45, 125), 'legs': (45, 30, 65), 'trim': (245, 125, 85),
                'head': 'fox', 'weapon': 'orb'},
    'reaper':  {'torso': (50, 38, 68), 'legs': (25, 25, 36), 'trim': (70, 225, 215),
                'head': 'hood', 'weapon': 'scythe'},
}

WEAPON_COL = {'sword': (200, 205, 220), 'dagger': (180, 180, 200),
              'staff': (150, 110, 60), 'bow': (140, 100, 55),
              'orb': (255, 120, 190), 'scythe': (90, 235, 225)}


def _player_frame(style, leg_a, leg_b, bob, weapon_out):
    st = _PLAYER_STYLE[style]
    s = _surf(24, 30)
    if style == 'kitsune':
        _r(s, 2, 14 + bob, 5, 11, (220, 105, 70))
        _r(s, 0, 12 + bob, 4, 8, (245, 180, 120))
    # Piernas
    _r(s, 8, 23 + leg_a + bob, 4, 7 - leg_a, st['legs'])
    _r(s, 13, 23 + leg_b + bob, 4, 7 - leg_b, st['legs'])
    # Torso + cinturón
    _r(s, 7, 12 + bob, 10, 12, st['torso'])
    _r(s, 7, 20 + bob, 10, 2, st['trim'])
    # Cabeza
    _r(s, 8, 4 + bob, 8, 8, SKIN)
    _r(s, 9, 7 + bob, 2, 2, DARK)  # ojo
    _r(s, 13, 7 + bob, 2, 2, DARK)
    head, weapon = st['head'], st['weapon']
    if head == 'helmet':
        _r(s, 7, 2 + bob, 10, 4, (150, 155, 175))
        _r(s, 11, 0 + bob, 2, 3, st['trim'])  # penacho
    elif head == 'hood':
        _r(s, 6, 2 + bob, 12, 6, st['trim'])
        _r(s, 6, 2 + bob, 12, 2, st['torso'])
    elif head == 'hat':
        _r(s, 5, 0 + bob, 14, 4, st['trim'])
        _r(s, 8, 0 + bob, 8, 2, (90, 50, 130))
    elif head == 'fox':
        _r(s, 7, 1 + bob, 4, 5, (225, 105, 70))
        _r(s, 14, 1 + bob, 4, 5, (225, 105, 70))
        _r(s, 8, 2 + bob, 2, 2, (250, 205, 165))
        _r(s, 15, 2 + bob, 2, 2, (250, 205, 165))
    # Arma
    wc = WEAPON_COL[weapon]
    if weapon_out:
        if weapon == 'sword':
            _r(s, 18, 8 + bob, 3, 14, wc)
            _r(s, 16, 20 + bob, 7, 2, (120, 90, 40))
        elif weapon == 'dagger':
            _r(s, 18, 14 + bob, 2, 7, wc)
        elif weapon == 'staff':
            _r(s, 19, 4 + bob, 2, 20, wc)
            _r(s, 18, 2 + bob, 4, 4, (180, 120, 255))
        elif weapon == 'bow':
            _r(s, 18, 8 + bob, 2, 12, wc)
            _r(s, 18, 8 + bob, 5, 2, wc)
        elif weapon == 'orb':
            _r(s, 18, 8 + bob, 5, 5, wc)
            _r(s, 20, 6 + bob, 2, 2, (255, 220, 140))
        elif weapon == 'scythe':
            _r(s, 19, 3 + bob, 2, 22, (75, 65, 85))
            _r(s, 15, 2 + bob, 7, 2, wc)
            _r(s, 14, 3 + bob, 3, 3, wc)
    else:
        if weapon == 'sword':
            _r(s, 4, 14 + bob, 2, 10, wc)
        elif weapon == 'dagger':
            _r(s, 4, 18 + bob, 2, 5, wc)
        elif weapon == 'staff':
            _r(s, 3, 10 + bob, 2, 16, wc)
        elif weapon == 'bow':
            _r(s, 2, 12 + bob, 2, 10, wc)
        elif weapon == 'orb':
            _r(s, 3, 10 + bob, 4, 4, wc)
        elif weapon == 'scythe':
            _r(s, 3, 5 + bob, 2, 21, (75, 65, 85))
            _r(s, 3, 4 + bob, 7, 2, wc)
    return s


def make_player_frames(char_class):
    style = char_class if char_class in _PLAYER_STYLE else 'warrior'
    return {
        'idle': [_player_frame(style, 0, 0, 0, False),
                 _player_frame(style, 0, 0, 1, False)],
        'run': [_player_frame(style, 0, 2, 0, False),
                _player_frame(style, 2, 0, 0, False),
                _player_frame(style, 0, 2, 1, False),
                _player_frame(style, 2, 0, 1, False)],
        'jump': [_player_frame(style, 2, 2, 0, False)],
        'attack': [_player_frame(style, 1, 0, 0, True)],
    }


# ============================================================================
# ENEMIGOS
# ============================================================================

def _slime_frame(squash):
    s = _surf(16, 16)
    w, h = (14, 9) if squash else (11, 12)
    x, y = (16 - w) // 2, 16 - h
    _r(s, x, y, w, h, (40, 200, 80))
    _r(s, x + 1, y + 1, w - 2, 3, (120, 255, 150))
    _r(s, x + 3, y + 4, 2, 3, DARK)
    _r(s, x + w - 5, y + 4, 2, 3, DARK)
    return s


def _skeleton_frame(step, color=(200, 200, 210)):
    s = _surf(16, 16)
    dark = (60, 60, 70)
    _r(s, 5, step, 6, 5, color)          # cráneo
    _r(s, 6, 1 + step, 2, 2, dark)
    _r(s, 9, 1 + step, 1, 2, dark)
    _r(s, 6, 6 + step, 4, 5, color)      # costillas
    _r(s, 4, 6 + step, 2, 1, color)
    _r(s, 10, 6 + step, 2, 1, color)
    _r(s, 5, 11, 2, 5 - step, dark)      # piernas
    _r(s, 9, 11, 2, 3 + step, dark)
    return s


def _bat_frame(wings_up):
    s = _surf(18, 14)
    body = (150, 80, 200)
    if wings_up:
        _r(s, 0, 0, 5, 8, (110, 55, 160))
        _r(s, 13, 0, 5, 8, (110, 55, 160))
    else:
        _r(s, 0, 6, 6, 4, (110, 55, 160))
        _r(s, 12, 6, 6, 4, (110, 55, 160))
    _r(s, 7, 4, 4, 7, body)
    _r(s, 8, 6, 1, 1, (255, 60, 60))
    _r(s, 10, 6, 1, 1, (255, 60, 60))
    _r(s, 7, 1, 1, 3, body)  # orejas
    _r(s, 10, 1, 1, 3, body)
    return s


def _goblin_frame(step):
    s = _skeleton_frame(step, color=(60, 160, 70))
    _r(s, 2, 2, 3, 2, (40, 130, 55))   # orejas
    _r(s, 11, 2, 3, 2, (40, 130, 55))
    _r(s, 6, 8, 4, 2, (200, 60, 60))   # taparrabos
    return s


def _zone_enemy_frame(enemy_type, pose):
    """Compact silhouettes for the five biome-exclusive enemies."""
    s = _surf(24, 24)
    bob = 1 if pose == 1 else 0
    attack = pose == 2
    if enemy_type == 'moss_boar':
        _r(s, 3, 10 + bob, 16, 9, (73, 105, 58))
        _r(s, 12, 7 + bob, 9, 9, (91, 145, 72))
        _r(s, 16, 9 + bob, 2, 2, (245, 210, 95))
        _r(s, 20, 13 + bob, 4, 2, (230, 220, 180))
        _r(s, 5, 18, 3, 5, DARK); _r(s, 15, 18, 3, 5, DARK)
        if attack: _r(s, 0, 14, 5, 2, (130, 175, 75))
    elif enemy_type == 'crystal_beetle':
        shell = (52, 132, 160) if not attack else (100, 225, 240)
        _r(s, 4, 8 + bob, 16, 12, shell)
        _r(s, 7, 5 + bob, 10, 5, (125, 235, 240))
        _r(s, 11, 7 + bob, 2, 13, (25, 70, 90))
        for x in (3, 8, 15, 20): _r(s, x, 19, 2, 4, DARK)
        _r(s, 1, 10 + bob, 4, 2, (180, 250, 255))
    elif enemy_type == 'ruin_drowned':
        _r(s, 8, 3 + bob, 8, 7, (95, 160, 158))
        _r(s, 7, 10 + bob, 10, 10, (43, 87, 92))
        _r(s, 9, 5 + bob, 2, 2, (150, 255, 220))
        _r(s, 14, 5 + bob, 2, 2, (150, 255, 220))
        arm_y = 9 if attack else 12
        _r(s, 3, arm_y + bob, 5, 3, (67, 126, 132)); _r(s, 17, arm_y + bob, 5, 3, (67, 126, 132))
        _r(s, 7, 20, 4, 4, DARK); _r(s, 14, 20, 4, 4, DARK)
    elif enemy_type == 'rune_acolyte':
        _r(s, 7, 5 + bob, 10, 7, (78, 38, 102))
        _r(s, 5, 11 + bob, 14, 12, (104, 54, 142))
        _r(s, 10, 7 + bob, 2, 2, (245, 170, 255)); _r(s, 14, 7 + bob, 2, 2, (245, 170, 255))
        _r(s, 2 if attack else 18, 8 + bob, 4, 4, (220, 120, 255))
        _r(s, 3 if attack else 19, 9 + bob, 2, 2, (255, 235, 255))
    else:  # storm_harpy
        wing_y = 2 if pose != 1 else 9
        _r(s, 8, 6 + bob, 8, 13, (75, 105, 165))
        _r(s, 1, wing_y, 8, 4, (124, 174, 225)); _r(s, 15, wing_y, 8, 4, (124, 174, 225))
        _r(s, 9, 3 + bob, 6, 6, (205, 220, 225))
        _r(s, 11, 5 + bob, 2, 2, (255, 240, 100))
        _r(s, 9, 18, 2, 5, (245, 205, 80)); _r(s, 14, 18, 2, 5, (245, 205, 80))
        if attack: _r(s, 2, 19, 20, 2, (255, 240, 100))
    return s


def make_enemy_frames(enemy_type):
    if enemy_type in ('moss_boar', 'crystal_beetle', 'ruin_drowned',
                      'rune_acolyte', 'storm_harpy'):
        frames = [_zone_enemy_frame(enemy_type, pose) for pose in range(4)]
        return {'idle': [frames[0], frames[1]], 'run': [frames[1], frames[0]],
                'jump': [frames[1]], 'attack': [frames[2]], 'hurt': [frames[3]]}
    if enemy_type == 'slime':
        return {'idle': [_slime_frame(False), _slime_frame(True)],
                'run': [_slime_frame(False), _slime_frame(True)],
                'jump': [_slime_frame(False)], 'attack': [_slime_frame(True)]}
    if enemy_type == 'bat':
        return {'idle': [_bat_frame(True), _bat_frame(False)],
                'run': [_bat_frame(True), _bat_frame(False)],
                'jump': [_bat_frame(True)], 'attack': [_bat_frame(False)]}
    if enemy_type == 'goblin':
        return {'idle': [_goblin_frame(0), _goblin_frame(0)],
                'run': [_goblin_frame(0), _goblin_frame(2)],
                'jump': [_goblin_frame(1)], 'attack': [_goblin_frame(2)]}
    return {'idle': [_skeleton_frame(0), _skeleton_frame(0)],   # skeleton y resto
            'run': [_skeleton_frame(0), _skeleton_frame(2)],
            'jump': [_skeleton_frame(1)], 'attack': [_skeleton_frame(2)]}


# ============================================================================
# JEFES
# ============================================================================

def _guardian_frame(step, attack):
    s = _surf(36, 52)
    body, dark = (150, 30, 60), (90, 15, 35)
    _r(s, 12, 26 + step, 12, 22, body)
    _r(s, 12, 26 + step, 12, 4, dark)
    _r(s, 13, 10, 10, 12, (220, 180, 150))
    _r(s, 8, 4, 4, 8, dark)    # cuernos
    _r(s, 24, 4, 4, 8, dark)
    _r(s, 14, 13, 3, 3, (255, 220, 60))
    _r(s, 20, 13, 3, 3, (255, 220, 60))
    _r(s, 8, 28 + step, 4, 16, dark)   # brazos
    _r(s, 24, 28 + step, 4, 16, dark)
    if attack:
        _r(s, 4, 14, 6, 14, dark)
        _r(s, 26, 14, 6, 14, dark)
    _r(s, 12, 46, 5, 6, dark)
    _r(s, 20, 46, 5, 6, dark)
    return s


def _mother_frame(step, attack):
    s = _surf(44, 40)
    w = 40 if step else 36
    x = (44 - w) // 2
    _r(s, x, 10, w, 26, (25, 130, 55))
    _r(s, x + 3, 12, w - 6, 8, (90, 220, 120))
    for ex in (x + 8, x + w - 12):
        _r(s, ex, 18, 4, 5, (255, 220, 60))
    _r(s, x + 6, 2, w - 12, 8, (200, 170, 60))  # corona de esporas
    if attack:
        _r(s, x - 4, 14, 4, 12, (25, 130, 55))
        _r(s, x + w, 14, 4, 12, (25, 130, 55))
    return s


def _void_frame(step, attack):
    s = _surf(40, 48)
    _r(s, 10, 6, 20, 36, (45, 12, 70))
    _r(s, 13, 9, 14, 30, (70, 20, 110))
    core = 6 + step * 2
    _r(s, 20 - core // 2, 22 - core // 2, core, core, (220, 40, 90))
    _r(s, 12, 4, 4, 4, (220, 40, 90))
    _r(s, 24, 4, 4, 4, (220, 40, 90))
    if attack:
        _r(s, 4, 16, 6, 16, (45, 12, 70))
        _r(s, 30, 16, 6, 16, (45, 12, 70))
    _r(s, 12, 42, 6, 6, (45, 12, 70))
    _r(s, 22, 42, 6, 6, (45, 12, 70))
    return s


def make_boss_frames(boss_id):
    if boss_id == 'cavern_mother':
        fn = _mother_frame
    elif boss_id == 'void_heart':
        fn = _void_frame
    else:
        fn = _guardian_frame
    return {'idle': [fn(0, False), fn(1, False)],
            'run': [fn(0, False), fn(1, False)],
            'jump': [fn(0, False)],
            'attack': [fn(0, True)]}
