"""Pure rules for enemy launch, juggle resistance, and collision impacts."""

MIN_IMPACT_SCALE = 0.28


def launch_response(weight, horizontal_force, vertical_force, juggle_resistance=0.0):
    """Return velocity components after weight and repeated-juggle resistance."""
    mass = max(0.35, float(weight))
    resistance = max(0.0, min(0.72, float(juggle_resistance)))
    scale = max(MIN_IMPACT_SCALE, (1.0 - resistance) / mass)
    return float(horizontal_force) * scale, float(vertical_force) * scale


def wall_bounce(velocity_x, weight):
    """Return rebound velocity and environmental damage for a wall impact."""
    speed = abs(float(velocity_x))
    if speed < 150.0:
        return 0.0, 0
    restitution = max(0.22, 0.42 - max(0.0, float(weight) - 1.0) * 0.08)
    rebound = -float(velocity_x) * restitution
    damage = max(1, round((speed - 120.0) / (34.0 * max(0.7, float(weight)))))
    return rebound, damage


def ground_impact(velocity_y, weight):
    """Return knockdown duration and environmental damage for a hard landing."""
    speed = max(0.0, float(velocity_y))
    if speed < 285.0:
        return 0.0, 0
    mass = max(0.5, float(weight))
    duration = min(1.15, 0.3 + (speed - 285.0) / 430.0) / max(0.8, mass ** 0.35)
    damage = max(1, round((speed - 245.0) / (42.0 * max(0.75, mass))))
    return duration, damage
