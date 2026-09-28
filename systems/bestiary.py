# bestiary.py - Registro de enemigos: se desbloquea al derrotar.
# Claves: 'enemy:<tipo>', 'elite:<afijo>:<tipo>', 'mini:<id>', 'boss:<id>'.

from systems.balance_data import (BOSS_DEFS, ELITE_AFFIXES, ENEMY_STATS,
    MINIBOSS_DEFS)

CATEGORIES = [
    ('common', 'Comunes'),
    ('elite', 'Élites'),
    ('mini', 'Minijefes'),
    ('boss', 'Jefes'),
]

BOSS_TIPS = {
    'cavern_mother': 'Abanicos de 3 esporas. En P2 salta encima: no estés debajo. Quema sus invocaciones.',
    'sanctum_guardian': 'Embestida con telegraph: pégate al muro para que se aturda solo. Nova de hielo ayuda.',
    'void_heart': 'Se teletransporta: escucha el destello. El meteoro avisa en rojo, corre sin parar.',
}

MINI_TIPS = {
    'colossal_slime': 'Al morir se divide en 2: guarda área o hechizos para las crías.',
    'broken_knight': 'Su embestida telegrafiada acaba en aturdimiento si choca un muro. Provócala.',
}

ELITE_TIPS = {
    'inferno': 'Quema al contacto: no lo roces ni con iframes justos, cúrate tras el golpe.',
    'veloz': 'Tan rápido que la persecución no sirve: espera su llegada y castiga.',
    'blindado': 'Mucha vida, poco más: DPS sostenido y paciencia.',
    'vampiro': 'Se cura golpeando: mátalo de lejos o de un estallido antes de que robe.',
    'maldito': 'Envenena al contacto: la inmunidad del rogue lo anula por completo.',
}


def _normals():
    entries = {}
    for etype, st in ENEMY_STATS.items():
        entries[f'enemy:{etype}'] = {
            'key': f'enemy:{etype}', 'category': 'common',
            'name': st.get('name', etype), 'color': st.get('color', (255, 255, 255)),
            'hp': st['health'], 'dmg': st['damage'], 'xp': st['xp'],
            'zones': st.get('zones', '???'),
            'trait': f"{st.get('trait', '—')} · Postura media",
            'tip': (st.get('tip', '') + ' Finales de combo y paradas rompen su postura.').strip(),
        }
    return entries


def _elites():
    entries = {}
    for af in ELITE_AFFIXES:
        for etype, st in ENEMY_STATS.items():
            key = f"elite:{af['id']}:{etype}"
            entries[key] = {
                'key': key, 'category': 'elite',
                'name': f"{af['name']} {st.get('name', etype)}",
                'color': af.get('outline', (255, 220, 100)),
                'hp': f"×{af.get('hp', 1.0)}", 'dmg': f"×{af.get('dmg', 1.0)}",
                'xp': f"×{af.get('xp', 1.0)}",
                'zones': 'Todas (más al este)',
                'trait': (('Roba vida' if af.get('lifesteal') else
                           'Aplica estado' if af.get('status') else
                           'Veloz' if af['id'] == 'veloz' else 'Aguante')
                          + ' · Postura alta'),
                'tip': ELITE_TIPS.get(af['id'], '') + ' Tras recuperarse resiste postura durante 3s.',
            }
    return entries


def _minis():
    entries = {}
    for mid, md in MINIBOSS_DEFS.items():
        entries[f'mini:{mid}'] = {
            'key': f'mini:{mid}', 'category': 'mini',
            'name': md['name'], 'color': md['color'],
            'hp': md['health'], 'dmg': md['damage'], 'xp': md['xp'],
            'zones': 'Cavernas' if mid == 'colossal_slime' else 'Ruinas',
            'trait': ('Se divide en 2 · Postura alta' if md.get('split')
                      else 'Embestida · Postura alta'),
            'tip': MINI_TIPS.get(mid, '') + ' Con postura crítica puede contraatacar.',
        }
    return entries


def _bosses():
    entries = {}
    for bid, bd in BOSS_DEFS.items():
        entries[f'boss:{bid}'] = {
            'key': f'boss:{bid}', 'category': 'boss',
            'name': bd['name'], 'color': bd.get('color', (255, 255, 255)),
            'hp': bd['health'], 'dmg': bd['damage'], 'xp': bd['xp'],
            'zones': {'cavern_mother': 'Cavernas', 'sanctum_guardian': 'Santuario',
                      'void_heart': 'Santuario profundo'}.get(bid, '???'),
            'trait': '3 fases · Postura extrema',
            'tip': BOSS_TIPS.get(bid, '') + ' Presión baja provoca una respuesta desesperada.',
        }
    return entries


def build_catalog():
    catalog = {}
    for part in (_normals(), _elites(), _minis(), _bosses()):
        catalog.update(part)
    return catalog


CATALOG = build_catalog()


def total_entries():
    return len(CATALOG)


def unlocked_count(kills):
    return sum(1 for k in CATALOG if kills.get(k, 0) > 0)
