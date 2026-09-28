"""Shared targeting rules for player attacks."""


def assisted_target(origin, requested, targets, facing=1, snap_radius=96.0,
                    max_range=700.0, deadzone=44.0):
    """Return a stable world target, snapping only near an enemy under the cursor."""
    ox, oy = origin
    tx, ty = requested
    if (tx - ox) ** 2 + (ty - oy) ** 2 < deadzone ** 2:
        tx, ty = ox + (1 if facing >= 0 else -1) * 180.0, oy

    best = None
    best_score = snap_radius ** 2
    for target in targets:
        if hasattr(target, 'alive') and not target.alive():
            continue
        rect = getattr(target, 'rect', None)
        if rect is None:
            continue
        cx, cy = rect.centerx, rect.centery
        if (cx - ox) ** 2 + (cy - oy) ** 2 > max_range ** 2:
            continue
        score = (cx - tx) ** 2 + (cy - ty) ** 2
        if score < best_score:
            best_score = score
            best = (cx, cy)
    return best if best is not None else (tx, ty)


def melee_facing(origin, targets, current_facing=1, horizontal_range=88.0,
                 vertical_range=54.0):
    """Face the closest plausible melee target without changing attack reach."""
    ox, oy = origin
    best_dx = None
    best_score = None
    for target in targets:
        if hasattr(target, 'alive') and not target.alive():
            continue
        rect = getattr(target, 'rect', None)
        if rect is None:
            continue
        dx, dy = rect.centerx - ox, rect.centery - oy
        if abs(dx) > horizontal_range or abs(dy) > vertical_range:
            continue
        score = abs(dx) + abs(dy) * 1.5
        if best_score is None or score < best_score:
            best_score, best_dx = score, dx
    if best_dx is None or best_dx == 0:
        return 1 if current_facing >= 0 else -1
    return 1 if best_dx > 0 else -1
