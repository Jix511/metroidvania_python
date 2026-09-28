"""Animation timing and procedural secondary motion shared by all combatants."""

import math

import pygame


ANIMATION_FPS = {
    'idle': 3.5,
    'run': 10.0,
    'jump': 7.0,
    'fall': 7.0,
    'attack': 12.0,
    'hurt': 14.0,
    'telegraph': 7.0,
}


def state_elapsed(entity, state, now):
    """Reset one-shot states and desynchronize ambient looping motion."""
    if getattr(entity, 'visual_anim_state', None) != state:
        entity.visual_anim_state = state
        entity.visual_anim_started = now
    elapsed = max(0.0, now - getattr(entity, 'visual_anim_started', now))
    if state in ('idle', 'run'):
        elapsed += getattr(entity, 'anim_phase', 0.0)
    return elapsed


def frame_index(frame_count, elapsed, animation, progress=None, loop=True):
    if frame_count <= 1:
        return 0
    if progress is not None:
        return min(frame_count - 1, max(0, int(progress * frame_count)))
    index = int(max(0.0, elapsed) * ANIMATION_FPS.get(animation, 6.0))
    return index % frame_count if loop else min(frame_count - 1, index)


def pick_frame(frames, animation, elapsed, progress=None, loop=True):
    available = frames.get(animation) or frames.get('idle') or next(iter(frames.values()))
    return available[frame_index(len(available), elapsed, animation, progress, loop)]


def add_secondary_motion(image, state, elapsed, velocity_x=0.0, velocity_y=0.0,
                         reduced_motion=False):
    """Add restrained squash, breathing and lean without blurring pixel art."""
    if reduced_motion:
        return image
    sx = sy = 1.0
    angle = 0.0
    phase = math.sin(elapsed * math.tau * 2.0)
    if state == 'idle':
        sy, sx = 1.0 + phase * 0.018, 1.0 - phase * 0.009
    elif state == 'run':
        sy, sx = 1.0 - abs(phase) * 0.025, 1.0 + abs(phase) * 0.018
        angle = max(-2.5, min(2.5, velocity_x * 0.012))
    elif state == 'jump':
        sy, sx = 1.045, 0.975
        angle = max(-3.0, min(3.0, velocity_x * 0.01))
    elif state == 'fall':
        sy, sx = 0.97, 1.035
    elif state == 'telegraph':
        sy, sx = 0.94 + phase * 0.015, 1.06 - phase * 0.01
    elif state == 'attack':
        angle = max(-3.0, min(3.0, velocity_x * 0.008))
    elif state == 'hurt':
        sx, sy = 1.07, 0.94

    width = max(1, round(image.get_width() * sx))
    height = max(1, round(image.get_height() * sy))
    result = pygame.transform.scale(image, (width, height))
    if angle:
        result = pygame.transform.rotate(result, -angle)
    return result
