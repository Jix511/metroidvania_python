"""Absolute project paths shared by persistence and resource systems."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / 'assets'
SPRITES_DIR = ASSETS_DIR / 'sprites'
DATA_DIR = PROJECT_ROOT / 'data'
SAVES_DIR = PROJECT_ROOT / 'saves'

PLAYER_SAVE_PATH = SAVES_DIR / 'player_save.json'
CONTROLS_SAVE_PATH = SAVES_DIR / 'controls.json'
SETTINGS_SAVE_PATH = SAVES_DIR / 'settings.json'
MUSIC_CACHE_DIR = ASSETS_DIR / 'music'
