# items.py - Sistema de equipamiento: slots, rarezas, afijos, generación y loot.

import random
import uuid

from systems.item_data import (AFFIXES, BASE_ITEMS, ECONOMY, MAX_UPGRADE,
    POTION_HEAL_FRAC, POTION_MAX, POTION_PRICE, RARITIES, RARITY_COST_MULT,
    RARITY_ORDER, REFRESH_BASE, REFRESH_PER_LEVEL, SHOP_STOCK_SLOTS,
    SLOT_BASE_PRICE, SLOT_NAMES, SLOTS, STARTING_KITS)

def _roll_rarity(luck=0.0):
    total = sum(v['weight'] for v in RARITIES.values())
    r = random.uniform(0, total) - luck
    acc = 0.0
    for rid, rdata in RARITIES.items():
        acc += rdata['weight']
        if r <= acc:
            return rid
    return 'common'

def generate_item(level=1, slot=None, rarity=None, luck=0.0):
    """Genera un item escalado a nivel. Retorna dict serializable."""
    level = max(1, int(level))
    slot = slot or random.choice(SLOTS)
    rarity = rarity or _roll_rarity(luck)
    rdata = RARITIES[rarity]
    base = random.choice(BASE_ITEMS[slot])

    # Stats base escalados
    stats = {}
    for k, v in base['stats'].items():
        if k == 'damage':
            stats[k] = v + level * 2
        elif k == 'max_health':
            stats[k] = v + level * 5
        elif k == 'speed':
            stats[k] = float(v)
        else:
            stats[k] = float(v)

    # Afijos
    n_min, n_max = rdata['affixes']
    n_affix = random.randint(n_min, n_max)
    chosen = random.sample(AFFIXES, min(n_affix, len(AFFIXES)))
    for af in chosen:
        for k, v in af['stats'].items():
            if k in ('damage', 'max_health'):
                # Escalar planos con nivel y rareza más adelante
                stats[k] = stats.get(k, 0) + v + (level // 2 if k == 'damage' else level * 2 if k == 'max_health' else 0)
            elif k == 'damage_taken':
                stats[k] = stats.get(k, 1.0) * v
            else:
                stats[k] = stats.get(k, 0.0) + v

    # Multiplicador de rareza a planos principales
    mult = rdata['mult']
    if 'damage' in stats:
        stats['damage'] = int(round(stats['damage'] * mult))
    if 'max_health' in stats:
        stats['max_health'] = int(round(stats['max_health'] * (1.0 + (mult - 1.0) * 0.7)))

    # Nombre
    prefix = f"{rdata['name']} " if rarity != 'common' else ""
    affix_names = " ".join(a['name'] for a in chosen[:2])
    name = f"{prefix}{base['name']}"
    if affix_names and rarity in ('rare', 'epic', 'legendary'):
        name = f"{name} {affix_names}"

    return {
        'id': str(uuid.uuid4())[:8],
        'base_id': base['base_id'],
        'name': name,
        'slot': slot,
        'rarity': rarity,
        'level': level,
        'stats': {k: (round(v, 3) if isinstance(v, float) else v) for k, v in stats.items()},
    }

def starting_kit(character_class):
    """Kit inicial por clase para no empezar desnudo."""
    kit = STARTING_KITS.get(character_class, STARTING_KITS['mage'])
    result = []
    for definition in kit:
        item = generate_item(1, definition['slot'], 'common')
        item['name'] = definition['name']
        item['stats'] = dict(definition['stats'])
        result.append(item)
    return result

def item_power(item):
    """Score simple para comparar / loot."""
    s = item.get('stats', {})
    return (s.get('damage', 0) * 3 + s.get('max_health', 0) * 0.5
            + s.get('speed', 0) * 0.3 + s.get('crit_chance', 0) * 100
            + s.get('evasion', 0) * 120 + s.get('xp_gain', 0) * 50)

def buy_price(item):
    s = SLOT_BASE_PRICE.get(item.get('slot'), 30)
    lvl = item.get('level', 1)
    mult = RARITIES.get(item.get('rarity'), {}).get('mult', 1.0)
    raw = ((s + lvl * ECONOMY['buy_level_increment'])
           * (ECONOMY['buy_base_factor'] + mult * ECONOMY['buy_rarity_factor'])
           + item_power(item) * ECONOMY['buy_power_factor'])
    return max(10, int(round(raw / 5.0)) * 5)

def sell_price(item):
    return max(5, buy_price(item) // ECONOMY['sell_divisor'])

def refresh_price(player_level):
    return REFRESH_BASE + max(1, player_level) * REFRESH_PER_LEVEL


def upgrade_level(item):
    return int(item.get('upgrade', 0))


def upgrade_cost(item):
    up = upgrade_level(item)
    mult = RARITY_COST_MULT.get(item.get('rarity'), 1.0)
    raw = (ECONOMY['upgrade_base_cost']
           * ((up + 1) ** ECONOMY['upgrade_exponent']) * mult)
    return max(10, int(round(raw / 5.0)) * 5)


def apply_upgrade(item):
    """Sube +1 una pieza (máx MAX_UPGRADE). Muta stats y nombre. Retorna False si al máximo."""
    up = upgrade_level(item)
    if up >= MAX_UPGRADE:
        return False
    st = item.get('stats', {})
    for k in ('damage', 'max_health'):
        if st.get(k):
            st[k] = int(st[k] * ECONOMY['upgrade_primary_multiplier']) + 1
    if st.get('speed'):
        st['speed'] = int(st['speed']) + (2 if st['speed'] >= 0 else -1)
    for k in ('crit_chance', 'evasion', 'crit_damage', 'fire_damage', 'xp_gain', 'gold_find'):
        if st.get(k):
            st[k] = round(st[k] * ECONOMY['upgrade_secondary_multiplier'], 3)
    item['stats'] = st
    item['upgrade'] = up + 1
    base_name = item.get('name', 'Objeto').split(' +')[0]
    item['name'] = f"{base_name} +{up + 1}"
    return True


def craft_result_rarity(rarity):
    i = RARITY_ORDER.index(rarity) if rarity in RARITY_ORDER else 0
    if i >= len(RARITY_ORDER) - 1:
        return None
    return RARITY_ORDER[i + 1]


def item_display_name(item):
    return item.get('name', 'Objeto')

def generate_shop_stock(player_level, luck=4.0):
    """6 artículos: 2 armas + 1 de cada resto, nivel del jugador, mejor suerte."""
    return [generate_item(max(1, player_level), slot=s, luck=luck)
            for s in SHOP_STOCK_SLOTS]

def format_stats(stats):
    parts = []
    if stats.get('damage'):
        parts.append(f"+{stats['damage']} DMG")
    if stats.get('max_health'):
        parts.append(f"+{stats['max_health']} HP")
    if stats.get('speed'):
        v = stats['speed']
        parts.append(f"{'+' if v >= 0 else ''}{int(v)} VEL")
    if stats.get('crit_chance'):
        parts.append(f"+{stats['crit_chance']*100:.0f}% CRIT")
    if stats.get('crit_damage'):
        parts.append(f"+{stats['crit_damage']*100:.0f}% daño CRIT")
    if stats.get('fire_damage'):
        parts.append(f"+{stats['fire_damage']*100:.0f}% fuego")
    if stats.get('evasion'):
        parts.append(f"+{stats['evasion']*100:.0f}% EVA")
    if stats.get('xp_gain'):
        parts.append(f"+{stats['xp_gain']*100:.0f}% XP")
    if stats.get('gold_find'):
        parts.append(f"+{stats['gold_find']*100:.0f}% ORO")
    if stats.get('damage_taken', 1.0) != 1.0:
        parts.append(f"-{(1-stats['damage_taken'])*100:.0f}% DMG recibido")
    return ", ".join(parts) if parts else "Sin bonus"
