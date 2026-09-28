"""Geometría pura para las zonas de impacto de ataques cuerpo a cuerpo."""

import math


def _angle_delta(a, b):
    return (a - b + 180.0) % 360.0 - 180.0


def arc_intersects_rect(origin, rect, facing, reach, arc_degrees,
                        aim_degrees=0.0, inner_radius=0.0):
    """Comprueba un rectángulo contra un sector orientado usando su radio visual."""
    ox, oy = origin
    rx, ry, rw, rh = rect
    cx, cy = rx + rw / 2.0, ry + rh / 2.0
    local_x = (cx - ox) * (1 if facing >= 0 else -1)
    local_y = cy - oy
    target_radius = math.hypot(rw, rh) * 0.5
    distance = math.hypot(local_x, local_y)
    if distance - target_radius > reach or distance + target_radius < inner_radius:
        return False
    if arc_degrees >= 359.0 or distance <= target_radius:
        return True
    angle = math.degrees(math.atan2(local_y, local_x))
    angular_padding = math.degrees(math.asin(min(1.0, target_radius / distance)))
    return abs(_angle_delta(angle, aim_degrees)) <= arc_degrees / 2.0 + angular_padding
