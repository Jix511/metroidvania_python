"""Validated item, loot, and economy configuration."""

import json

from constants import CHARACTER_CLASSES
from core.paths import DATA_DIR


class ItemDataError(ValueError):
    pass


def _load_document():
    path = DATA_DIR / 'items.json'
    try:
        with path.open('r', encoding='utf-8') as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ItemDataError(f'Could not load {path.name}: {exc}') from exc
    if not isinstance(document, dict):
        raise ItemDataError('items.json must contain an object')
    return document


def _require(document, key, expected_type):
    value = document.get(key)
    if not isinstance(value, expected_type):
        raise ItemDataError(f'items.json.{key} has an invalid type')
    return value


def _rgb(label, value):
    if (not isinstance(value, list) or len(value) != 3
            or not all(isinstance(channel, int) and 0 <= channel <= 255
                       for channel in value)):
        raise ItemDataError(f'{label} must be an RGB color')
    return tuple(value)


_DOCUMENT = _load_document()
SLOTS = _require(_DOCUMENT, 'slots', list)
SLOT_NAMES = _require(_DOCUMENT, 'slot_names', dict)
RARITIES = _require(_DOCUMENT, 'rarities', dict)
BASE_ITEMS = _require(_DOCUMENT, 'base_items', dict)
AFFIXES = _require(_DOCUMENT, 'affixes', list)
STARTING_KITS = _require(_DOCUMENT, 'starting_kits', dict)
ECONOMY = _require(_DOCUMENT, 'economy', dict)

if not SLOTS or len(SLOTS) != len(set(SLOTS)):
    raise ItemDataError('slots must be non-empty and unique')
if set(SLOT_NAMES) != set(SLOTS) or set(BASE_ITEMS) != set(SLOTS):
    raise ItemDataError('slot_names and base_items must define every slot')

for rarity_id, rarity in RARITIES.items():
    required = {'name', 'mult', 'affixes', 'weight', 'color'}
    if not isinstance(rarity, dict) or not required.issubset(rarity):
        raise ItemDataError(f'rarity {rarity_id} is incomplete')
    affix_range = rarity['affixes']
    if (not isinstance(affix_range, list) or len(affix_range) != 2
            or affix_range[0] > affix_range[1] or affix_range[0] < 0):
        raise ItemDataError(f'rarity {rarity_id} has an invalid affix range')
    rarity['affixes'] = tuple(affix_range)
    rarity['color'] = _rgb(f'rarity {rarity_id}.color', rarity['color'])
    if rarity['weight'] <= 0 or rarity['mult'] <= 0:
        raise ItemDataError(f'rarity {rarity_id} requires positive weight and mult')

if sum(rarity['weight'] for rarity in RARITIES.values()) != 100:
    raise ItemDataError('rarity weights must add up to 100')

base_ids = set()
for slot, entries in BASE_ITEMS.items():
    if not isinstance(entries, list) or not entries:
        raise ItemDataError(f'base_items.{slot} must be a non-empty list')
    for item in entries:
        if not isinstance(item, dict) or not {'base_id', 'name', 'stats'}.issubset(item):
            raise ItemDataError(f'base item in {slot} is incomplete')
        if item['base_id'] in base_ids:
            raise ItemDataError(f'duplicate base item: {item["base_id"]}')
        if not all(isinstance(value, (int, float)) for value in item['stats'].values()):
            raise ItemDataError(f'base item {item["base_id"]} has non-numeric stats')
        base_ids.add(item['base_id'])

affix_ids = set()
for affix in AFFIXES:
    if not isinstance(affix, dict) or not {'id', 'name', 'stats'}.issubset(affix):
        raise ItemDataError('an item affix is incomplete')
    if affix['id'] in affix_ids:
        raise ItemDataError(f'duplicate item affix: {affix["id"]}')
    if not all(isinstance(value, (int, float)) for value in affix['stats'].values()):
        raise ItemDataError(f'affix {affix["id"]} has non-numeric stats')
    affix_ids.add(affix['id'])

if set(STARTING_KITS) != set(CHARACTER_CLASSES):
    raise ItemDataError('starting_kits must match CHARACTER_CLASSES')
for class_id, kit in STARTING_KITS.items():
    if not isinstance(kit, list) or not kit:
        raise ItemDataError(f'starting kit {class_id} must be a non-empty list')
    for entry in kit:
        if (not isinstance(entry, dict) or entry.get('slot') not in SLOTS
                or not isinstance(entry.get('name'), str)
                or not isinstance(entry.get('stats'), dict)):
            raise ItemDataError(f'starting kit {class_id} contains an invalid item')

_economy_fields = {
    'potion_price', 'potion_heal_fraction', 'potion_max', 'refresh_base',
    'refresh_per_level', 'max_upgrade', 'rarity_order',
    'rarity_cost_multipliers', 'slot_base_prices', 'shop_stock_slots',
    'buy_level_increment', 'buy_base_factor', 'buy_rarity_factor',
    'buy_power_factor', 'sell_divisor', 'upgrade_base_cost',
    'upgrade_exponent', 'upgrade_primary_multiplier',
    'upgrade_secondary_multiplier',
}
if not _economy_fields.issubset(ECONOMY):
    missing = sorted(_economy_fields - set(ECONOMY))
    raise ItemDataError(f'economy is missing: {", ".join(missing)}')
if set(ECONOMY['rarity_order']) != set(RARITIES):
    raise ItemDataError('economy.rarity_order must contain every rarity')
if set(ECONOMY['rarity_cost_multipliers']) != set(RARITIES):
    raise ItemDataError('economy rarity multipliers must contain every rarity')
if set(ECONOMY['slot_base_prices']) != set(SLOTS):
    raise ItemDataError('economy slot prices must contain every slot')
if any(slot not in SLOTS for slot in ECONOMY['shop_stock_slots']):
    raise ItemDataError('economy.shop_stock_slots contains an unknown slot')
for field in _economy_fields - {'rarity_order', 'rarity_cost_multipliers',
                                'slot_base_prices', 'shop_stock_slots'}:
    if not isinstance(ECONOMY[field], (int, float)) or ECONOMY[field] <= 0:
        raise ItemDataError(f'economy.{field} must be positive')

POTION_PRICE = ECONOMY['potion_price']
POTION_HEAL_FRAC = ECONOMY['potion_heal_fraction']
POTION_MAX = ECONOMY['potion_max']
REFRESH_BASE = ECONOMY['refresh_base']
REFRESH_PER_LEVEL = ECONOMY['refresh_per_level']
MAX_UPGRADE = ECONOMY['max_upgrade']
RARITY_ORDER = ECONOMY['rarity_order']
RARITY_COST_MULT = ECONOMY['rarity_cost_multipliers']
SLOT_BASE_PRICE = ECONOMY['slot_base_prices']
SHOP_STOCK_SLOTS = ECONOMY['shop_stock_slots']
