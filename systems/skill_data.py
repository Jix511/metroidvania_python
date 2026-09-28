"""Validated skill-tree configuration."""

import json

from constants import CHARACTER_CLASSES
from core.paths import DATA_DIR


class SkillDataError(ValueError):
    pass


def _load_document():
    path = DATA_DIR / 'skills.json'
    try:
        with path.open('r', encoding='utf-8') as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SkillDataError(f'Could not load {path.name}: {exc}') from exc
    if not isinstance(document, dict):
        raise SkillDataError('skills.json must contain an object')
    return document


def _validate_skill(skill_id, skill, categories):
    required = {'id', 'name', 'description', 'cost', 'max_rank', 'requires',
                'category', 'effects', 'icon'}
    if not isinstance(skill, dict) or not required.issubset(skill):
        raise SkillDataError(f'skill {skill_id} is incomplete')
    if skill['id'] != skill_id:
        raise SkillDataError(f'skill key and id differ: {skill_id}')
    if (not isinstance(skill['cost'], int) or skill['cost'] < 1
            or not isinstance(skill['max_rank'], int) or skill['max_rank'] < 1):
        raise SkillDataError(f'skill {skill_id} has invalid cost or max_rank')
    if skill['category'] not in categories:
        raise SkillDataError(f'skill {skill_id} has an unknown category')
    if not isinstance(skill['requires'], list) or not isinstance(skill['effects'], dict):
        raise SkillDataError(f'skill {skill_id} has invalid requirements or effects')


def _validate_tree(class_id, universal, tree, categories):
    overlap = set(universal) & set(tree)
    if overlap:
        raise SkillDataError(
            f'{class_id} duplicates universal skills: {", ".join(sorted(overlap))}')
    available = {**universal, **tree}
    for skill_id, skill in tree.items():
        _validate_skill(skill_id, skill, categories)
    for skill_id, skill in available.items():
        for required_id in skill['requires']:
            if required_id not in available:
                raise SkillDataError(
                    f'{class_id}.{skill_id} requires unknown skill {required_id}')

    visiting = set()
    visited = set()

    def visit(skill_id):
        if skill_id in visiting:
            raise SkillDataError(f'{class_id} skill tree contains a cycle at {skill_id}')
        if skill_id in visited:
            return
        visiting.add(skill_id)
        for required_id in available[skill_id]['requires']:
            visit(required_id)
        visiting.remove(skill_id)
        visited.add(skill_id)

    for skill_id in available:
        visit(skill_id)


_DOCUMENT = _load_document()
SKILL_CATEGORIES = _DOCUMENT.get('categories')
UNIVERSAL_SKILLS = _DOCUMENT.get('universal')
CLASS_SKILL_TREES = _DOCUMENT.get('classes')

if (not isinstance(SKILL_CATEGORIES, list) or not SKILL_CATEGORIES
        or len(SKILL_CATEGORIES) != len(set(SKILL_CATEGORIES))):
    raise SkillDataError('skills categories must be non-empty and unique')
if not isinstance(UNIVERSAL_SKILLS, dict):
    raise SkillDataError('skills universal section must be an object')
if not isinstance(CLASS_SKILL_TREES, dict):
    raise SkillDataError('skills classes section must be an object')
if set(CLASS_SKILL_TREES) != set(CHARACTER_CLASSES):
    raise SkillDataError('skills classes must match CHARACTER_CLASSES')

for skill_id, skill in UNIVERSAL_SKILLS.items():
    _validate_skill(skill_id, skill, SKILL_CATEGORIES)
for class_id, tree in CLASS_SKILL_TREES.items():
    if not isinstance(tree, dict):
        raise SkillDataError(f'skill tree {class_id} must be an object')
    _validate_tree(class_id, UNIVERSAL_SKILLS, tree, SKILL_CATEGORIES)

WARRIOR_SKILLS = CLASS_SKILL_TREES['warrior']
ROGUE_SKILLS = CLASS_SKILL_TREES['rogue']
MAGE_SKILLS = CLASS_SKILL_TREES['mage']
RANGER_SKILLS = CLASS_SKILL_TREES['ranger']
KITSUNE_SKILLS = CLASS_SKILL_TREES['kitsune']
REAPER_SKILLS = CLASS_SKILL_TREES['reaper']
