# music.py - Música procedural adaptativa (exploración / combate / jefe).
# Sin assets: se sintetiza una vez y se cachea en assets/music/*.wav.

import math
import os
import struct
import wave

from core.paths import MUSIC_CACHE_DIR

SR = 22050
CACHE_DIR = str(MUSIC_CACHE_DIR)

# Nota -> frecuencia (iguales temperados, A4=440).
_NOTES = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
          'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}


def freq(note, octave):
    midi = (octave + 1) * 12 + _NOTES[note]
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def _add_tone(buf, start, f0, f1, dur, kind='sine', vol=0.3, decay=2.0):
    n = max(1, int(SR * dur))
    phase = 0.0
    for i in range(start, min(len(buf), start + n)):
        k = (i - start) / n
        f = f0 + (f1 - f0) * k
        phase += 2.0 * math.pi * f / SR
        if kind == 'sine':
            v = math.sin(phase)
        elif kind == 'square':
            v = (1.0 if math.sin(phase) > 0 else -1.0) * 0.5
        elif kind == 'saw':
            v = (2.0 * ((phase / (2.0 * math.pi)) % 1.0) - 1.0) * 0.5
        else:
            v = math.sin(phase)
        buf[i] += v * vol * math.exp(-decay * k)


def _add_noise(buf, start, dur, vol=0.2, decay=5.0, brightness=0.5):
    import random
    n = max(1, int(SR * dur))
    last = 0.0
    for i in range(start, min(len(buf), start + n)):
        k = (i - start) / n
        last = last * (1.0 - brightness) + random.uniform(-1, 1) * brightness
        buf[i] += last * vol * math.exp(-decay * k)


def _finish(buf):
    # Fundidos de 30ms en los bordes para bucles sin clicks.
    f = max(1, int(SR * 0.03))
    for i in range(min(f, len(buf))):
        buf[i] *= i / f
        buf[-1 - i] *= i / f
    peak = max(0.001, max(abs(v) for v in buf))
    if peak > 0.85:
        buf = [v / peak * 0.85 for v in buf]
    raw = struct.pack('<%dh' % len(buf), *[max(-32768, min(32767, int(v * 32767))) for v in buf])
    bio = __import__('io').BytesIO()
    with wave.open(bio, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(raw)
    bio.seek(0)
    return bio.read()


def _render_explore():
    # 90 BPM, Am - F - C - G, 4 compases. Pad + arpegio, sin batería.
    beat = 60.0 / 90.0
    bar = beat * 4
    buf = [0.0] * int(SR * bar * 4)
    chords = [('A', 'C', 'E'), ('F', 'A', 'C'), ('C', 'E', 'G'), ('G', 'B', 'D')]
    for b, (r, t3, t5) in enumerate(chords):
        base = int(b * bar * SR)
        for note, octv, vol in ((r, 2, 0.20), (t3, 3, 0.14), (t5, 3, 0.14), (r, 3, 0.10)):
            _add_tone(buf, base, freq(note, octv), freq(note, octv), bar, 'sine', vol, 1.2)
        # Arpegio de corcheas
        for i, nn in enumerate([r, t3, t5, r, t5, t3, r, t3]):
            octv = 4 if i % 3 == 2 else 3
            _add_tone(buf, base + int(i * beat / 2 * SR), freq(nn, octv), freq(nn, octv),
                      beat / 2, 'sine', 0.12, 4.0)
    return _finish(buf)


def _render_combat():
    # 132 BPM, Am Am F E. Bajo motor + kick + hats + arpegio 16avos.
    beat = 60.0 / 132.0
    bar = beat * 4
    buf = [0.0] * int(SR * bar * 4)
    roots = ['A', 'A', 'F', 'E']
    for b, r in enumerate(roots):
        base = int(b * bar * SR)
        for i in range(8):  # bajo en corcheas
            _add_tone(buf, base + int(i * beat / 2 * SR), freq(r, 1), freq(r, 1), beat / 2, 'saw', 0.20, 3.0)
        for i in range(4):  # kick en cada pulso
            _add_tone(buf, base + int(i * beat * SR), 120, 40, 0.12, 'sine', 0.5, 6.0)
        for i in range(8):  # hats a contratiempo
            _add_noise(buf, base + int((i + 0.5) * beat / 2 * SR), 0.03, 0.12, 8.0, 0.8)
        scale = [r, 'C', 'D', 'E', 'G', 'A']
        for i in range(16):  # arpegio 16avos
            nn = scale[i % len(scale)]
            _add_tone(buf, base + int(i * beat / 4 * SR), freq(nn, 4), freq(nn, 4), beat / 4, 'square', 0.07, 5.0)
    return _finish(buf)


def _render_boss():
    # 150 BPM, Em F Em D. Bajo 16avos + kick a piso + caja + arp rápido + stabs.
    beat = 60.0 / 150.0
    bar = beat * 4
    buf = [0.0] * int(SR * bar * 4)
    roots = ['E', 'F', 'E', 'D']
    for b, r in enumerate(roots):
        base = int(b * bar * SR)
        for i in range(16):
            _add_tone(buf, base + int(i * beat / 4 * SR), freq(r, 1), freq(r, 1), beat / 4, 'saw', 0.22, 3.0)
        for i in range(4):
            _add_tone(buf, base + int(i * beat * SR), 130, 38, 0.12, 'sine', 0.55, 6.0)
        for i in (1, 3):  # caja en 2 y 4
            _add_noise(buf, base + int(i * beat * SR), 0.12, 0.35, 4.0, 0.6)
        for i in range(8):
            _add_noise(buf, base + int((i + 0.5) * beat / 2 * SR), 0.03, 0.10, 8.0, 0.8)
        for i in range(16):
            nn = ['E', 'F', 'G', 'A', 'B', 'C'][i % 6]
            _add_tone(buf, base + int(i * beat / 4 * SR), freq(nn, 5), freq(nn, 5), beat / 4, 'square', 0.06, 5.0)
        _add_tone(buf, base, freq(r, 4), freq(r, 4), beat, 'saw', 0.12, 2.0)  # stab
    return _finish(buf)


_BUILDERS = {'explore': _render_explore, 'combat': _render_combat, 'boss': _render_boss}


def ensure_cache():
    os.makedirs(CACHE_DIR, exist_ok=True)
    for mode, fn in _BUILDERS.items():
        path = os.path.join(CACHE_DIR, mode + '.wav')
        if not (os.path.exists(path) and os.path.getsize(path) > 1000):
            with open(path, 'wb') as f:
                f.write(fn())


class AdaptiveMusic:
    """Tres bucles en canales dedicados con crossfade según el modo."""
    MODES = ('explore', 'combat', 'boss')

    def __init__(self, base_volume=0.32):
        import pygame
        ensure_cache()
        if pygame.mixer.get_num_channels() < 16:
            pygame.mixer.set_num_channels(16)
        try:
            pygame.mixer.set_reserved(3)  # 0,1,2 solo para música
        except Exception:
            pass
        self.base_volume = base_volume
        self.muted = False
        self.mode = 'explore'
        self.menu_duck = 1.0
        self.boss_intensity = 1.0
        self.channels = {}
        self.sounds = {}
        for i, mode in enumerate(self.MODES):
            path = os.path.join(CACHE_DIR, mode + '.wav')
            snd = pygame.mixer.Sound(path)
            ch = pygame.mixer.Channel(i)
            ch.play(snd, loops=-1)
            ch.set_volume(0.0)
            self.channels[mode] = ch
            self.sounds[mode] = snd

    def set_mode(self, mode, menu=False):
        if mode in self.MODES:
            self.mode = mode
        self.menu_duck = 0.6 if menu else 1.0

    def set_muted(self, m):
        self.muted = bool(m)

    def set_boss_phase(self, phase):
        self.boss_intensity = min(1.25, 1.0 + max(0, int(phase) - 1) * 0.12)

    def set_volume(self, master, music):
        self.base_volume = 0.46 * max(0.0, min(1.0, float(master))) * max(
            0.0, min(1.0, float(music)))

    def update(self, dt):
        rate = 1.4 * dt
        for mode, ch in self.channels.items():
            intensity = self.boss_intensity if mode == 'boss' else 1.0
            target = (self.base_volume * self.menu_duck * intensity
                      if (mode == self.mode and not self.muted) else 0.0)
            cur = ch.get_volume()
            if abs(target - cur) <= rate:
                ch.set_volume(target)
            else:
                ch.set_volume(cur + rate if target > cur else cur - rate)

    def stop(self):
        for ch in self.channels.values():
            try:
                ch.stop()
            except Exception:
                pass
