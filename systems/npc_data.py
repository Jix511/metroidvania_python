"""Validated NPC placement and reactive dialogue definitions."""

import json

from core.paths import DATA_DIR
from constants import TILE_SIZE
from world.world_data import MAP_HEIGHT, MAP_WIDTH, ZONE_DEFS


class NPCDataError(ValueError):
    pass


def _load_npcs():
    path = DATA_DIR / 'npcs.json'
    try:
        with path.open('r', encoding='utf-8') as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise NPCDataError(f'Could not load {path.name}: {exc}') from exc
    zones = {zone['id']: zone for zone in ZONE_DEFS}
    if not isinstance(document, dict) or not document:
        raise NPCDataError('npcs.json must contain NPC definitions')
    for npc_id, npc in document.items():
        required = {'name', 'role', 'zone_id', 'tx', 'ty', 'refuge_tx',
                    'refuge_ty', 'color', 'dialogue', 'lore'}
        if not isinstance(npc, dict) or not required.issubset(npc):
            raise NPCDataError(f'NPC {npc_id} is incomplete')
        zone = zones.get(npc['zone_id'])
        if (zone is None or not isinstance(npc['tx'], int)
                or not zone['x0'] <= npc['tx'] <= zone['x1']
                or not isinstance(npc['ty'], int) or not 0 <= npc['ty'] < MAP_HEIGHT):
            raise NPCDataError(f'NPC {npc_id} is outside its zone')
        color = npc['color']
        if (not isinstance(color, list) or len(color) != 3
                or not all(isinstance(value, int) and 0 <= value <= 255 for value in color)):
            raise NPCDataError(f'NPC {npc_id} has an invalid color')
        dialogue = npc['dialogue']
        if (not isinstance(dialogue, dict) or 'default' not in dialogue
                or any(not isinstance(lines, list) or not lines
                       or any(not isinstance(line, str) for line in lines)
                       for lines in dialogue.values())):
            raise NPCDataError(f'NPC {npc_id} has invalid dialogue')
        if not isinstance(npc['lore'], list) or not npc['lore']:
            raise NPCDataError(f'NPC {npc_id} has no lore dialogue')
        npc['color'] = tuple(color)
        npc['x'] = npc['tx'] * TILE_SIZE + TILE_SIZE // 2
        npc['y'] = npc['ty'] * TILE_SIZE
        meadow = zones['meadow']
        if (not meadow['x0'] <= npc['refuge_tx'] <= meadow['x1']
                or not 0 <= npc['refuge_ty'] < MAP_HEIGHT):
            raise NPCDataError(f'NPC {npc_id} has an invalid refuge position')
        npc['refuge_x'] = npc['refuge_tx'] * TILE_SIZE + TILE_SIZE // 2
        npc['refuge_y'] = npc['refuge_ty'] * TILE_SIZE
    return document


NPCS = _load_npcs()


def dialogue_for(player, npc):
    dialogue = npc['dialogue']
    rescue_quest = npc.get('rescue_quest')
    if (rescue_quest and getattr(player, 'quest_states', {}).get(rescue_quest) == 'completed'
            and 'refuge' in dialogue):
        return dialogue['refuge']
    bosses = player.boss_defeated_ids
    if len(bosses) >= 3 and 'all_bosses' in dialogue:
        return dialogue['all_bosses']
    for event_id in ('sanctum_guardian', 'broken_knight', 'cavern_mother'):
        if (event_id in bosses or event_id in player.miniboss_defeated_ids) and event_id in dialogue:
            return dialogue[event_id]
    return dialogue['default']


def npc_at_refuge(player, npc):
    quest_id = npc.get('rescue_quest')
    return quest_id is None or getattr(player, 'quest_states', {}).get(quest_id) == 'completed'


def npc_position(player, npc):
    if npc_at_refuge(player, npc):
        return npc['refuge_x'], npc['refuge_y']
    return npc['x'], npc['y']


def refuge_members(player):
    return [npc_id for npc_id, npc in NPCS.items() if npc_at_refuge(player, npc)]
