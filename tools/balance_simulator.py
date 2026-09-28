"""Headless balance simulator driven by the project's validated data files."""

import argparse
import json
import math
import random
import sys
from pathlib import Path

from constants import CHARACTER_CLASSES
from world.world_data import ENEMY_SPAWNS, MINIBOSS_SPAWNS
from systems.balance_data import BOSS_DEFS, ENEMY_STATS, MINIBOSS_DEFS
from systems.item_data import RARITIES, RARITY_ORDER, STARTING_KITS
from systems.items import buy_price, generate_item, item_power, upgrade_cost
from systems.skill_data import CLASS_SKILL_TREES, UNIVERSAL_SKILLS


def enemy_metrics(enemy_id, ng_cycle=0):
    stats = ENEMY_STATS[enemy_id]
    return {
        'id': enemy_id,
        'name': stats['name'],
        'health': int(stats['health'] * (1 + 0.6 * ng_cycle)),
        'damage': int(round(stats['damage'] * (1 + 0.35 * ng_cycle))),
        'xp': int(stats['xp'] * (1 + 0.5 * ng_cycle)),
    }


def miniboss_metrics(miniboss_id, ng_cycle=0):
    stats = MINIBOSS_DEFS[miniboss_id]
    return {
        'id': miniboss_id,
        'name': stats['name'],
        'health': int(stats['health'] * (1 + 0.6 * ng_cycle)),
        'damage': int(round(stats['damage'] * (1 + 0.35 * ng_cycle))),
        'xp': int(stats.get('xp', 50) * (1 + 0.5 * ng_cycle)),
    }


def boss_metrics(boss_id, ng_cycle=0):
    stats = BOSS_DEFS[boss_id]
    return {
        'id': boss_id,
        'name': stats['name'],
        'health': int(stats['health'] * (1 + 0.8 * ng_cycle)),
        'damage': int(round(stats['damage'] * (1 + 0.4 * ng_cycle))),
        'xp': int(stats['xp'] * (1 + 0.5 * ng_cycle)),
        'gold': int(stats['gold'] * (1 + 0.5 * ng_cycle)),
    }


def class_metrics(class_id):
    class_data = CHARACTER_CLASSES[class_id]
    kit = STARTING_KITS[class_id]
    return {
        'id': class_id,
        'name': class_data['name'],
        'health': class_data['health'] + sum(
            entry['stats'].get('max_health', 0) for entry in kit),
        'damage': class_data['damage'] + sum(
            entry['stats'].get('damage', 0) for entry in kit),
        'speed': class_data['speed'] + sum(
            entry['stats'].get('speed', 0) for entry in kit),
    }


def xp_curve(target_level=10):
    threshold = 100
    total = 0
    rows = []
    for level in range(2, max(2, target_level) + 1):
        total += threshold
        rows.append({'level': level, 'required': threshold, 'total': total})
        threshold = int(threshold * 1.4)
    return rows


def skill_costs(class_id):
    class_tree = CLASS_SKILL_TREES[class_id]
    universal_cost = sum(skill['cost'] * skill['max_rank']
                         for skill in UNIVERSAL_SKILLS.values())
    class_cost = sum(skill['cost'] * skill['max_rank']
                     for skill in class_tree.values())
    return {
        'universal': universal_cost,
        'class': class_cost,
        'total': universal_cost + class_cost,
    }


def campaign_rewards(player_level=1, ng_cycle=0):
    normal_xp = sum(enemy_metrics(enemy_id, ng_cycle)['xp']
                    for enemy_id, _tx in ENEMY_SPAWNS)
    miniboss_xp = sum(miniboss_metrics(miniboss_id, ng_cycle)['xp']
                      for miniboss_id, _tx in MINIBOSS_SPAWNS)
    boss_xp = sum(boss_metrics(boss_id, ng_cycle)['xp'] for boss_id in BOSS_DEFS)
    boss_gold = sum(boss_metrics(boss_id, ng_cycle)['gold'] for boss_id in BOSS_DEFS)
    average_drop_gold = int(round(
        (4 + max(1, player_level) * 1.5) * (1 + 0.3 * ng_cycle)))
    normal_gold = average_drop_gold * len(ENEMY_SPAWNS)
    return {
        'normal_xp': normal_xp,
        'miniboss_xp': miniboss_xp,
        'boss_xp': boss_xp,
        'total_xp': normal_xp + miniboss_xp + boss_xp,
        'normal_gold_estimate': normal_gold,
        'boss_gold': boss_gold,
        'total_gold_estimate': normal_gold + boss_gold,
    }


def item_samples(level, samples=40, seed=1337):
    state = random.getstate()
    random.seed(seed + level)
    try:
        result = {}
        for rarity in RARITY_ORDER:
            generated = [generate_item(level, rarity=rarity) for _ in range(samples)]
            result[rarity] = {
                'average_power': round(
                    sum(item_power(item) for item in generated) / samples, 2),
                'average_buy_price': round(
                    sum(buy_price(item) for item in generated) / samples, 2),
                'weight': RARITIES[rarity]['weight'],
            }
        return result
    finally:
        random.setstate(state)


def build_report(player_level=1, ng_cycle=0):
    classes = {class_id: class_metrics(class_id) for class_id in CHARACTER_CLASSES}
    enemies = {enemy_id: enemy_metrics(enemy_id, ng_cycle) for enemy_id in ENEMY_STATS}
    minibosses = {
        miniboss_id: miniboss_metrics(miniboss_id, ng_cycle)
        for miniboss_id in MINIBOSS_DEFS
    }
    bosses = {boss_id: boss_metrics(boss_id, ng_cycle) for boss_id in BOSS_DEFS}

    for target in list(enemies.values()) + list(minibosses.values()) + list(bosses.values()):
        target['hits_by_class'] = {
            class_id: math.ceil(target['health'] / max(1, values['damage']))
            for class_id, values in classes.items()
        }

    rewards = campaign_rewards(player_level, ng_cycle)
    skills = {class_id: skill_costs(class_id) for class_id in CHARACTER_CLASSES}
    items = {level: item_samples(level) for level in (1, 5, 10)}
    alerts = []

    xp_to_level_5 = xp_curve(5)[-1]['total']
    if rewards['total_xp'] < xp_to_level_5:
        alerts.append('La campaña completa no alcanza la XP estimada para nivel 5.')
    for class_id, values in skills.items():
        points_at_level_10 = 9 * 3
        if values['class'] > points_at_level_10:
            alerts.append(
                f'{classes[class_id]["name"]}: su árbol de clase requiere '
                f'{values["class"]} puntos; a nivel 10 se obtienen {points_at_level_10}.')
    if max(c['damage'] for c in classes.values()) >= 2 * min(
            c['damage'] for c in classes.values()):
        alerts.append('La diferencia de daño inicial entre clases es de 2x o más.')

    sample_item = generate_item(max(1, player_level), slot='weapon', rarity='common')
    economy = {
        'sample_common_weapon_price': buy_price(sample_item),
        'sample_common_weapon_upgrade': upgrade_cost(sample_item),
        'campaign_gold_estimate': rewards['total_gold_estimate'],
    }

    return {
        'parameters': {'player_level': player_level, 'ng_cycle': ng_cycle},
        'classes': classes,
        'enemies': enemies,
        'minibosses': minibosses,
        'bosses': bosses,
        'progression': {
            'xp_curve': xp_curve(10),
            'campaign_rewards': rewards,
            'skill_costs': skills,
        },
        'item_samples': items,
        'economy': economy,
        'alerts': alerts,
    }


def _table(headers, rows):
    widths = [len(header) for header in headers]
    text_rows = [[str(cell) for cell in row] for row in rows]
    for row in text_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    line = ' | '.join(header.ljust(widths[index])
                      for index, header in enumerate(headers))
    separator = '-+-'.join('-' * width for width in widths)
    body = [' | '.join(cell.ljust(widths[index])
                       for index, cell in enumerate(row)) for row in text_rows]
    return '\n'.join([line, separator, *body])


def render_text(report):
    lines = [
        'SIMULADOR DE BALANCE',
        f"Nivel del jugador: {report['parameters']['player_level']} | "
        f"NG+: {report['parameters']['ng_cycle']}",
        '',
        'CLASES INICIALES',
        _table(
            ['Clase', 'HP', 'Daño', 'Velocidad'],
            [(value['name'], value['health'], value['damage'], value['speed'])
             for value in report['classes'].values()],
        ),
        '',
        'ENEMIGOS',
        _table(
            ['Enemigo', 'HP', 'Daño', 'XP', 'Golpes G/R/M/A'],
            [(value['name'], value['health'], value['damage'], value['xp'],
              '/'.join(str(value['hits_by_class'][class_id])
                       for class_id in CHARACTER_CLASSES))
             for value in report['enemies'].values()],
        ),
        '',
        'JEFES',
        _table(
            ['Jefe', 'HP', 'Daño', 'XP', 'Oro'],
            [(value['name'], value['health'], value['damage'], value['xp'], value['gold'])
             for value in report['bosses'].values()],
        ),
        '',
        'PROGRESIÓN',
        f"XP total de campaña: {report['progression']['campaign_rewards']['total_xp']}",
        f"Oro estimado de campaña: {report['economy']['campaign_gold_estimate']}",
        '',
        'COSTE DE HABILIDADES',
        _table(
            ['Clase', 'Universales', 'Clase', 'Total'],
            [(report['classes'][class_id]['name'], values['universal'],
              values['class'], values['total'])
             for class_id, values in report['progression']['skill_costs'].items()],
        ),
        '',
        'PODER MEDIO DE OBJETOS',
        _table(
            ['Nivel', 'Rareza', 'Poder', 'Precio'],
            [(level, RARITIES[rarity]['name'], values['average_power'],
              values['average_buy_price'])
             for level, rarities in report['item_samples'].items()
             for rarity, values in rarities.items()],
        ),
        '',
        'ECONOMÍA',
        f"Arma común de muestra: {report['economy']['sample_common_weapon_price']}g",
        f"Primera mejora: {report['economy']['sample_common_weapon_upgrade']}g",
        '',
        'ALERTAS',
    ]
    lines.extend(f'- {alert}' for alert in report['alerts'])
    if not report['alerts']:
        lines.append('- Sin alertas con los umbrales actuales.')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description='Simula el balance del metroidvania.')
    parser.add_argument('--level', type=int, default=1, help='Nivel del jugador.')
    parser.add_argument('--ng', type=int, default=0, help='Ciclo de Nuevo Juego+.')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    parser.add_argument('--output', type=Path, help='Archivo de salida opcional.')
    args = parser.parse_args(argv)

    report = build_report(max(1, args.level), max(0, args.ng))
    if args.format == 'json':
        output = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    else:
        output = render_text(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding='utf-8')
    else:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        print(output, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
