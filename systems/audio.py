# audio.py - SFX procedurales (stdlib puro, sin assets). Tolerante si no hay mixer.

import io
import math
import random
import struct
import wave

SR = 22050
_sounds = {}
_muted = False
_ready = False
_master_volume = 1.0
_sfx_volume = 1.0
_last_variant = {}

CLASS_ATTACK_SOUNDS = {
    'warrior': ('warrior_swing_1', 'warrior_swing_2', 'warrior_swing_3'),
    'rogue': ('rogue_swing_1', 'rogue_swing_2', 'rogue_swing_3'),
    'ranger': ('ranger_shot_1', 'ranger_shot_2'),
    'mage': ('mage_cast_1', 'mage_cast_2'),
    'kitsune': ('kitsune_cast_1', 'kitsune_cast_2'),
    'reaper': ('reaper_swing_1', 'reaper_swing_2', 'reaper_swing_3'),
}

CLASS_IMPACT_SOUNDS = {
    'warrior': 'warrior_hit',
    'rogue': 'rogue_hit',
    'ranger': 'ranger_hit',
    'mage': 'mage_hit',
    'kitsune': 'kitsune_hit',
    'reaper': 'reaper_hit',
}

REACTION_SOUNDS = {
    'toxic_blast': 'reaction_toxic_blast',
    'thermal_shock': 'reaction_thermal_shock',
    'chain_lightning': 'reaction_chain_lightning',
    'shatter': 'reaction_shatter',
}

AMBIENT_SOUNDS = {
    'meadow': 'ambient_meadow',
    'caves': 'ambient_caves',
    'ruins': 'ambient_ruins',
    'sanctum': 'ambient_sanctum',
    'peak': 'ambient_peak',
    'refuge': 'ambient_refuge',
}


def _pack(samples):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(struct.pack('<%dh' % len(samples),
                                  *[max(-32768, min(32767, int(s * 32767))) for s in samples]))
    buf.seek(0)
    return buf.read()


def _tone(f0, f1, dur, kind='sine', vol=0.5, decay=3.0):
    n = max(1, int(SR * dur))
    out = []
    phase = 0.0
    for i in range(n):
        k = i / n
        f = f0 + (f1 - f0) * k
        phase += 2.0 * math.pi * f / SR
        if kind == 'sine':
            v = math.sin(phase)
        elif kind == 'square':
            v = 1.0 if math.sin(phase) > 0 else -1.0
            v *= 0.6
        elif kind == 'saw':
            v = 2.0 * ((phase / (2.0 * math.pi)) % 1.0) - 1.0
            v *= 0.7
        else:
            v = math.sin(phase)
        env = math.exp(-decay * k)
        out.append(v * vol * env)
    return out


def _noise(dur, vol=0.4, decay=4.0, lowpass=0.25):
    n = max(1, int(SR * dur))
    out = []
    last = 0.0
    for i in range(n):
        k = i / n
        w = random.uniform(-1.0, 1.0)
        last = last * (1.0 - lowpass) + w * lowpass
        out.append(last * vol * math.exp(-decay * k))
    return out


def _mix(*tracks):
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, v in enumerate(t):
            out[i] += v
    peak = max(0.001, max(abs(v) for v in out))
    if peak > 0.95:
        out = [v / peak * 0.95 for v in out]
    return out


def _seq(notes, kind='sine', vol=0.45, note_dur=0.12, gap=0.02):
    """Arpegio: lista de frecuencias."""
    out = []
    unit = int(SR * (note_dur + gap))
    for f in notes:
        t = _tone(f, f, note_dur, kind, vol, decay=2.0)
        out.extend(t)
        out.extend([0.0] * int(SR * gap))
    return out[:len(out) - int(SR * gap)] if out else out


def _build():
    sounds = {
        'swing': _noise(0.09, vol=0.35, decay=6.0, lowpass=0.4),
        'hit': _mix(_tone(220, 90, 0.08, 'square', 0.5), _noise(0.06, 0.3, 6.0, 0.5)),
        'kill': _tone(500, 120, 0.22, 'saw', 0.45),
        'hurt': _tone(160, 60, 0.16, 'square', 0.5),
        'coin': _seq([880, 1320], 'sine', 0.4, 0.06),
        'pickup': _tone(400, 900, 0.14, 'sine', 0.45),
        'potion': _tone(300, 700, 0.22, 'sine', 0.45) + _tone(700, 350, 0.12, 'sine', 0.35),
        'levelup': _seq([523, 659, 784], 'square', 0.35, 0.11),
        'buy': _seq([880, 1174], 'sine', 0.42, 0.07),
        'sell': _seq([660, 440], 'sine', 0.4, 0.07),
        'skill': _seq([784, 1046], 'sine', 0.4, 0.09),
        'gate': _tone(80, 300, 0.5, 'saw', 0.4, decay=1.5),
        'checkpoint': _seq([392, 523, 659], 'sine', 0.4, 0.14),
        'dash': _noise(0.16, vol=0.4, decay=3.0, lowpass=0.6),
        'teleport': _tone(1200, 300, 0.2, 'sine', 0.4),
        'shoot': _tone(900, 300, 0.1, 'square', 0.3),
        'slam': _mix(_tone(70, 35, 0.4, 'sine', 0.6, decay=2.0), _noise(0.25, 0.4, 3.0, 0.3)),
        'nova': _mix(_tone(1200, 300, 0.35, 'sine', 0.45, decay=2.5), _noise(0.2, 0.25, 4.0, 0.5)),
        'meteor': _mix(_tone(60, 30, 0.7, 'sine', 0.6, decay=1.8), _noise(0.5, 0.45, 2.5, 0.25)),
        'roar': _tone(110, 55, 0.7, 'saw', 0.5, decay=1.2),
        'click': _tone(1200, 1200, 0.03, 'square', 0.25, decay=8.0),
        'victory': _seq([523, 659, 784, 1046], 'square', 0.35, 0.13),
        'gameover': _seq([392, 330, 262, 196], 'saw', 0.35, 0.16),
        'travel': _tone(500, 1000, 0.25, 'sine', 0.4),
    }
    sounds.update({
        'warrior_swing_1': _mix(_tone(175, 80, 0.13, 'saw', 0.35), _noise(0.1, 0.25, 5.0, 0.5)),
        'warrior_swing_2': _mix(_tone(145, 65, 0.16, 'saw', 0.4), _noise(0.12, 0.28, 4.5, 0.5)),
        'warrior_swing_3': _mix(_tone(120, 45, 0.2, 'saw', 0.45), _noise(0.16, 0.32, 4.0, 0.45)),
        'rogue_swing_1': _tone(850, 280, 0.075, 'saw', 0.32),
        'rogue_swing_2': _tone(1050, 360, 0.065, 'saw', 0.3),
        'rogue_swing_3': _mix(_tone(950, 220, 0.1, 'saw', 0.34), _noise(0.06, 0.2, 7.0, 0.6)),
        'ranger_shot_1': _mix(_tone(1250, 360, 0.09, 'square', 0.25), _noise(0.045, 0.15, 8.0, 0.7)),
        'ranger_shot_2': _mix(_tone(1100, 300, 0.1, 'square', 0.23), _tone(180, 90, 0.07, 'sine', 0.18)),
        'mage_cast_1': _seq([660, 990], 'sine', 0.3, 0.055, 0.0),
        'mage_cast_2': _mix(_tone(420, 1150, 0.13, 'sine', 0.32), _tone(900, 500, 0.12, 'sine', 0.18)),
        'kitsune_cast_1': _mix(_tone(760, 1280, 0.14, 'sine', 0.3), _noise(0.1, 0.12, 5.0, 0.2)),
        'kitsune_cast_2': _seq([880, 1175, 1568], 'sine', 0.24, 0.045, 0.0),
        'reaper_swing_1': _mix(_tone(360, 95, 0.18, 'saw', 0.32), _noise(0.12, 0.2, 4.0, 0.45)),
        'reaper_swing_2': _mix(_tone(430, 75, 0.2, 'saw', 0.35), _tone(980, 260, 0.12, 'sine', 0.15)),
        'reaper_swing_3': _mix(_tone(290, 48, 0.28, 'saw', 0.42), _noise(0.2, 0.28, 3.0, 0.5)),
        'warrior_hit': _mix(_tone(125, 48, 0.13, 'square', 0.48), _noise(0.1, 0.38, 5.0, 0.45)),
        'rogue_hit': _mix(_tone(420, 145, 0.075, 'square', 0.34), _noise(0.055, 0.26, 7.0, 0.65)),
        'ranger_hit': _mix(_tone(560, 180, 0.09, 'sine', 0.35), _noise(0.06, 0.22, 6.0, 0.55)),
        'mage_hit': _mix(_tone(780, 260, 0.12, 'sine', 0.32), _noise(0.08, 0.18, 5.0, 0.35)),
        'kitsune_hit': _mix(_tone(960, 310, 0.13, 'sine', 0.32), _tone(1250, 700, 0.1, 'sine', 0.18)),
        'reaper_hit': _mix(_tone(620, 80, 0.18, 'square', 0.35), _tone(1150, 240, 0.14, 'sine', 0.2)),
        'critical': _mix(_tone(1450, 240, 0.16, 'square', 0.38), _noise(0.12, 0.28, 5.0, 0.7)),
        'block': _mix(_tone(190, 190, 0.12, 'square', 0.34), _tone(880, 430, 0.08, 'sine', 0.22)),
        'immune': _seq([260, 210], 'square', 0.22, 0.07, 0.015),
        'reaction_toxic_blast': _mix(_tone(180, 520, 0.3, 'saw', 0.35), _noise(0.28, 0.3, 3.0, 0.25)),
        'reaction_thermal_shock': _mix(_tone(1000, 180, 0.28, 'sine', 0.38), _noise(0.2, 0.25, 4.0, 0.65)),
        'reaction_chain_lightning': _seq([1200, 680, 1450, 820], 'square', 0.23, 0.035, 0.008),
        'reaction_shatter': _mix(_tone(1500, 320, 0.18, 'square', 0.3), _noise(0.18, 0.4, 5.0, 0.75)),
        'ambient_meadow': _seq([1175, 1397, 1047], 'sine', 0.12, 0.09, 0.12),
        'ambient_caves': _mix(_tone(210, 115, 0.55, 'sine', 0.15, 1.2), _noise(0.45, 0.08, 1.5, 0.12)),
        'ambient_ruins': _seq([330, 294, 392], 'sine', 0.12, 0.16, 0.08),
        'ambient_sanctum': _mix(_tone(523, 523, 0.55, 'sine', 0.12, 1.0), _tone(784, 659, 0.5, 'sine', 0.09, 1.2)),
        'ambient_peak': _mix(_tone(140, 90, 0.7, 'sine', 0.1, 0.8), _noise(0.7, 0.13, 1.0, 0.08)),
        'ambient_refuge': _seq([392, 523, 659], 'sine', 0.13, 0.12, 0.06),
    })
    return sounds


def init():
    global _ready
    if _ready:
        return True
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        for name, samples in _build().items():
            _sounds[name] = pygame.mixer.Sound(buffer=_pack(samples))
            _sounds[name].set_volume(0.5)
        _ready = True
        return True
    except Exception:
        return False


def play(name, volume=1.0):
    if _muted or not _ready:
        return
    s = _sounds.get(name)
    if s is None:
        return
    try:
        level = _master_volume * _sfx_volume * max(0.0, min(1.0, volume))
        s.set_volume(0.5 * level)
        s.play()
    except Exception:
        pass


def play_variant(names, volume=1.0, key=None, index=None):
    """Reproduce una variante evitando repetirla cuando sea posible."""
    options = tuple(names)
    if not options:
        return None
    if index is not None:
        name = options[index % len(options)]
    else:
        group = key or options
        previous = _last_variant.get(group)
        choices = [name for name in options if name != previous] or list(options)
        name = random.choice(choices)
        _last_variant[group] = name
    play(name, volume)
    return name


def play_class_attack(character_class, combo_step=0, volume=0.7):
    names = CLASS_ATTACK_SOUNDS.get(character_class, ('swing',))
    melee = character_class in ('warrior', 'rogue', 'reaper')
    return play_variant(names, volume, key=('attack', character_class),
                        index=combo_step if melee else None)


def play_impact(character_class, critical=False, blocked=False, volume=0.8):
    if blocked:
        name = 'block'
    elif critical:
        name = 'critical'
    else:
        name = CLASS_IMPACT_SOUNDS.get(character_class, 'hit')
    play(name, volume)
    return name


def play_reaction(reaction_id, volume=0.8):
    name = REACTION_SOUNDS.get(reaction_id, 'skill')
    play(name, volume)
    return name


def play_ambient(zone_id, refuge=False, volume=0.18):
    name = AMBIENT_SOUNDS.get('refuge' if refuge else zone_id)
    if name:
        play(name, volume)
    return name


def toggle_mute():
    global _muted
    _muted = not _muted
    return _muted


def is_muted():
    return _muted


def set_volume(master, sfx):
    global _master_volume, _sfx_volume
    _master_volume = max(0.0, min(1.0, float(master)))
    _sfx_volume = max(0.0, min(1.0, float(sfx)))
