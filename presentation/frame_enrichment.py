"""Expand sparse sprite sheets into fuller pixel-art animation cycles."""

import math

import pygame


TARGET_COUNTS = {
    'idle': 6,
    'run': 8,
    'jump': 4,
    'hurt': 3,
    'attack': 7,
    'death': 6,
}


def _pose(source, animation, index, count):
    canvas = pygame.Surface(source.get_size(), pygame.SRCALPHA)
    bounds = source.get_bounding_rect(min_alpha=1)
    if not bounds.width or not bounds.height:
        return source.copy()
    subject = source.subsurface(bounds).copy()
    phase = math.sin(index / max(1, count - 1) * math.tau)
    sx = sy = 1.0
    dx = dy = angle = 0
    if animation == 'idle':
        sy, sx = 1.0 + phase * 0.018, 1.0 - phase * 0.009
        dy = round(abs(phase))
    elif animation == 'run':
        sy, sx = 1.0 - abs(phase) * 0.035, 1.0 + abs(phase) * 0.025
        dy = -round(abs(phase) * 2)
        angle = phase * 1.5
    elif animation == 'jump':
        sy, sx = (1.04, 0.97) if index < count / 2 else (0.97, 1.035)
        dy = -2 if index < count / 2 else 1
    elif animation == 'attack':
        progress = index / max(1, count - 1)
        dx = round(math.sin(progress * math.pi) * 5)
        sx = 1.0 + math.sin(progress * math.pi) * 0.035
        angle = -2.5 * math.sin(progress * math.pi)
    elif animation == 'hurt':
        dx = (-2, 2, 0)[min(index, 2)]
        sx, sy = 1.045, 0.96
    elif animation == 'death':
        progress = index / max(1, count - 1)
        sx, sy = 1.0 + progress * 0.18, 1.0 - progress * 0.5
        dy = round(progress * 4)

    size = (max(1, round(subject.get_width() * sx)),
            max(1, round(subject.get_height() * sy)))
    subject = pygame.transform.scale(subject, size)
    if angle:
        subject = pygame.transform.rotate(subject, angle)
    if animation == 'death':
        subject.set_alpha(round(255 * (1.0 - index / count * 0.55)))
    target = subject.get_rect(midbottom=(canvas.get_width() // 2 + dx,
                                         canvas.get_height() + dy))
    canvas.blit(subject, target)
    return canvas


def enrich_frames(animations):
    """Return new animation lists while preserving every authored source frame."""
    result = {name: list(frames) for name, frames in animations.items()}
    if 'death' not in result:
        result['death'] = list(result.get('hurt') or result.get('idle', []))[-1:]
    for animation, target_count in TARGET_COUNTS.items():
        sources = result.get(animation) or result.get('idle')
        if not sources:
            continue
        if len(sources) >= target_count:
            continue
        expanded = []
        for index in range(target_count):
            source_index = min(len(sources) - 1,
                               int(index * len(sources) / target_count))
            expanded.append(_pose(sources[source_index], animation,
                                  index, target_count))
        result[animation] = expanded
    return result
