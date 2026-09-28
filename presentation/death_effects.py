"""Short-lived animated remains used after combat entities are removed."""

import pygame


def create_death_echo(image, center, direction=1, boss=False, color=(255, 160, 90),
                      frames=None):
    duration = 1.25 if boss else 0.65
    return {
        'image': image.copy(),
        'frames': [frame.copy() for frame in (frames or [image])],
        'x': float(center[0]),
        'y': float(center[1]),
        'vx': float(direction) * (-115.0 if boss else -85.0),
        'vy': -210.0 if boss else -145.0,
        'rotation': 0.0,
        'spin': float(direction) * (95.0 if boss else 150.0),
        'time': duration,
        'duration': duration,
        'color': color,
    }


def update_death_echo(echo, dt):
    echo['time'] -= dt
    echo['vy'] += 520.0 * dt
    echo['x'] += echo['vx'] * dt
    echo['y'] += echo['vy'] * dt
    echo['rotation'] += echo['spin'] * dt
    echo['vx'] *= max(0.0, 1.0 - 2.2 * dt)
    return echo['time'] > 0


def draw_death_echo(surface, echo, offset):
    ratio = max(0.0, min(1.0, echo['time'] / echo['duration']))
    progress = 1.0 - ratio
    frames = echo.get('frames') or [echo['image']]
    frame_index = min(len(frames) - 1, int(progress * len(frames)))
    image = frames[frame_index].copy()
    image.set_alpha(round(255 * min(1.0, ratio * 1.7)))
    if echo['rotation']:
        image = pygame.transform.rotate(image, echo['rotation'])
    pos = (round(echo['x'] + offset[0]), round(echo['y'] + offset[1]))
    surface.blit(image, image.get_rect(center=pos))
