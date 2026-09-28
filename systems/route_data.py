"""Validated rewards and lookup helpers for ability-gated exploration routes."""

from systems.rewards import validate_reward
from world.world_data import ABILITY_ROUTES


ROUTES = {
    route['id']: {
        **route,
        'start': tuple(route['start']),
        'goal': tuple(route['goal']),
        'reward': validate_reward(f'ability route {route["id"]}', route['reward']),
    }
    for route in ABILITY_ROUTES
}
