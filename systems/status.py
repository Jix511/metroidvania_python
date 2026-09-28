# status.py - Efectos de estado: quemadura, veneno, ralentización, aturdimiento, marca.
# Un StatusList vive en cada entidad (enemigo, jefe, jugador) y se consulta cada frame.

STATUS_DEFS = {
    'burn':   {'name': 'Quemadura',   'dot': 8.0, 'slow': 1.0,  'stun': False,
               'dmg_taken': 1.0, 'duration': 3.0, 'max_stacks': 3, 'color': (255, 140, 40)},
    'poison': {'name': 'Veneno',      'dot': 5.0, 'slow': 1.0,  'stun': False,
               'dmg_taken': 1.0, 'duration': 4.0, 'max_stacks': 3, 'color': (90, 220, 90)},
    'slow':   {'name': 'Ralentizado', 'dot': 0.0, 'slow': 0.5,  'stun': False,
               'dmg_taken': 1.0, 'duration': 2.0, 'max_stacks': 1, 'color': (140, 200, 255)},
    'chill':  {'name': 'Helado',      'dot': 0.0, 'slow': 0.7,  'stun': False,
               'dmg_taken': 1.0, 'duration': 1.5, 'max_stacks': 1, 'color': (180, 230, 255)},
    'stun':   {'name': 'Aturdido',    'dot': 0.0, 'slow': 0.0,  'stun': True,
               'dmg_taken': 1.0, 'duration': 1.0, 'max_stacks': 1, 'color': (255, 230, 80)},
    'mark':   {'name': 'Marcado',     'dot': 0.0, 'slow': 1.0,  'stun': False,
               'dmg_taken': 1.5, 'duration': 5.0, 'max_stacks': 1, 'color': (255, 70, 70)},
    'shock':  {'name': 'Electrizado', 'dot': 2.0, 'slow': 0.9, 'stun': False,
               'dmg_taken': 1.08, 'duration': 2.0, 'max_stacks': 2, 'color': (255, 235, 95)},
}

# Prioridad de tinte visual cuando hay varios estados.
TINT_ORDER = ['stun', 'shock', 'burn', 'poison', 'slow', 'chill']


class StatusList:
    def __init__(self):
        self.active = {}  # id -> {'t': restante, 'stacks': int}

    def apply(self, sid, duration=None, stacks=1):
        """Aplica o refresca un estado. Retorna True si es nuevo."""
        d = STATUS_DEFS.get(sid)
        if not d:
            return False
        is_new = sid not in self.active
        cur = self.active.get(sid, {'t': 0.0, 'stacks': 0})
        cur['stacks'] = min(d['max_stacks'], cur['stacks'] + stacks)
        if cur['stacks'] < 1:
            cur['stacks'] = 1
        cur['t'] = duration if duration is not None else d['duration']
        self.active[sid] = cur
        return is_new

    def has(self, sid):
        return sid in self.active

    def remove(self, sid):
        return self.active.pop(sid, None) is not None

    def update(self, dt):
        """Avanza timers. Retorna daño por DoT acumulado en este tick."""
        dot = 0.0
        for sid in list(self.active.keys()):
            st = self.active[sid]
            st['t'] -= dt
            if st['t'] <= 0:
                del self.active[sid]
                continue
            dot += STATUS_DEFS[sid]['dot'] * st['stacks'] * dt
        return dot

    def speed_mult(self):
        m = 1.0
        for sid in self.active:
            m *= STATUS_DEFS[sid]['slow']
        return m

    def damage_taken_mult(self):
        m = 1.0
        for sid in self.active:
            m *= STATUS_DEFS[sid]['dmg_taken']
        return m

    def stunned(self):
        return any(STATUS_DEFS[sid]['stun'] for sid in self.active)

    def tint(self):
        for sid in TINT_ORDER:
            if sid in self.active:
                return STATUS_DEFS[sid]['color']
        return None

    def summary(self):
        """[(nombre, segundos, color)] para HUD."""
        return [(STATUS_DEFS[sid]['name'], st['t'], STATUS_DEFS[sid]['color'])
                for sid, st in self.active.items()]

    def to_dict(self):
        return {sid: {'t': round(st['t'], 2), 'stacks': st['stacks']} for sid, st in self.active.items()}

    def from_dict(self, data):
        self.active = {}
        for sid, st in (data or {}).items():
            if sid in STATUS_DEFS:
                self.active[sid] = {'t': float(st.get('t', 0)), 'stacks': int(st.get('stacks', 1))}
