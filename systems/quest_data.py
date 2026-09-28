"""Validated external quest definitions and progress evaluation."""

import json

from core.paths import DATA_DIR
from systems.npc_data import NPCS
from systems.rewards import validate_reward


class QuestDataError(ValueError):
    pass


CONDITION_TYPES = {'boss', 'miniboss', 'item_name', 'boss_count', 'encounter'}


def _load_quests():
    path = DATA_DIR / 'quests.json'
    try:
        with path.open('r', encoding='utf-8') as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QuestDataError(f'Could not load {path.name}: {exc}') from exc
    if not isinstance(document, dict) or not document:
        raise QuestDataError('quests.json must contain quests')
    result = {}
    for quest_id, quest in document.items():
        required = {'title', 'summary', 'giver', 'prerequisites', 'condition', 'reward', 'dialogue'}
        if not isinstance(quest, dict) or not required.issubset(quest):
            raise QuestDataError(f'quest {quest_id} is incomplete')
        condition = quest['condition']
        if quest['giver'] not in NPCS:
            raise QuestDataError(f'quest {quest_id} has an unknown giver')
        if not isinstance(condition, dict) or condition.get('type') not in CONDITION_TYPES:
            raise QuestDataError(f'quest {quest_id} has an invalid condition')
        dialogue = quest['dialogue']
        if (not isinstance(dialogue, dict)
                or not all(isinstance(dialogue.get(key), list) and dialogue[key]
                           and all(isinstance(line, str) for line in dialogue[key])
                           for key in ('offer', 'ready', 'completed'))):
            raise QuestDataError(f'quest {quest_id} has invalid dialogue')
        result[quest_id] = {
            **quest,
            'reward': validate_reward(f'quest {quest_id}.reward', quest['reward']),
        }
    for quest_id, quest in result.items():
        if (not isinstance(quest['prerequisites'], list)
                or any(req not in result for req in quest['prerequisites'])):
            raise QuestDataError(f'quest {quest_id} has invalid prerequisites')
    return result


QUESTS = _load_quests()


def condition_progress(player, condition):
    kind = condition['type']
    if kind == 'boss':
        return int(condition['id'] in player.boss_defeated_ids), 1
    if kind == 'miniboss':
        return int(condition['id'] in player.miniboss_defeated_ids), 1
    if kind == 'boss_count':
        target = int(condition['count'])
        return min(len(player.boss_defeated_ids), target), target
    if kind == 'encounter':
        return int(condition['id'] in getattr(player, 'completed_encounters', set())), 1
    items = list(player.inventory) + [item for item in player.equipment.values() if item]
    found = (condition['name'] in getattr(player, 'collected_items', set())
             or any(item.get('name') == condition['name'] for item in items))
    return int(found), 1


def quest_status(player, quest_id):
    state = player.quest_states.get(quest_id)
    if state == 'completed':
        return 'completed'
    quest = QUESTS[quest_id]
    if any(player.quest_states.get(req) != 'completed' for req in quest['prerequisites']):
        return 'locked'
    if state != 'active':
        return 'available'
    current, target = condition_progress(player, quest['condition'])
    return 'ready' if current >= target else 'active'
