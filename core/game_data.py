"""Static encounter and progression data used by the game coordinator."""

from systems.balance_data import BOSS_DEFS
from world.world_data import (
    BOSS_ARENAS,
    ENEMY_SPAWNS,
    LOAD_SPAWNS,
    MINIBOSS_SPAWNS,
    VICTORY_TEXT,
)

CLASS_ORDER = ['warrior', 'rogue', 'mage', 'ranger', 'kitsune', 'reaper']

TOTAL_BOSSES = len(BOSS_DEFS)
