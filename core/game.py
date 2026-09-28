# game.py - Clase Game: estado, update(dt), combate, cámara. main.py solo inicia.

import pygame
from constants import CHARACTER_CLASSES, FPS, SCREEN_HEIGHT, SCREEN_WIDTH, TILE_SIZE
from world.tilemap import Camera, TileMap
from world.mechanisms import create_moving_platforms
from presentation.ui import UI
from presentation.fx import Particles, FloatTexts
from presentation.combat_visuals import CombatVisuals
from presentation.environment import EnvironmentRenderer
from presentation.sprites import make_player_frames, make_enemy_frames, make_boss_frames
from presentation.sprite_loader import load_entity_frames, load_player_frames
from presentation.art_loader import load_art_assets
from core.game_events import GameEventsMixin
from core.game_render import GameRenderMixin
from core.game_update import GameUpdateMixin
from core.game_combat import GameCombatMixin
from core.game_state import GameStateMixin
from core.game_economy import GameEconomyMixin
from core.game_spells import GameSpellsMixin
from core.game_bosses import GameBossesMixin
from core.game_audio import GameAudioMixin
from core.game_narrative import GameNarrativeMixin
from core.game_exploration import GameExplorationMixin
from core.game_encounters import GameEncountersMixin
from core.game_routes import GameRoutesMixin
from core.paths import PLAYER_SAVE_PATH
from core.screen_state import GameScreen, ScreenStateMixin
from systems import audio
from systems import settings
from systems.balance_data import ENEMY_STATS
try:
    from systems.music import AdaptiveMusic
except Exception:
    AdaptiveMusic = None

class Game(
    ScreenStateMixin,
    GameStateMixin,
    GameEventsMixin,
    GameEconomyMixin,
    GameSpellsMixin,
    GameBossesMixin,
    GameCombatMixin,
    GameRenderMixin,
    GameUpdateMixin,
    GameAudioMixin,
    GameNarrativeMixin,
    GameExplorationMixin,
    GameEncountersMixin,
    GameRoutesMixin,
):
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass
        self.settings = settings.load()
        self.window = None
        self.screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._viewport = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self._apply_display_settings()
        pygame.display.set_caption("Metroidvania Python - Game(dt)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        self.font_small = pygame.font.Font(None, 18)
        self.font_big = pygame.font.Font(None, 36)
        self.font_title = pygame.font.Font(None, 48)
        self.ui = UI(self.screen, self.font, self.font_small, self.font_big,
                     self.font_title, mouse_pos=self._logical_mouse_pos)
        audio.init()

        self.game_map = TileMap()
        self.moving_platforms = create_moving_platforms()
        self.camera = Camera(
            self.game_map.width * TILE_SIZE,
            self.game_map.height * TILE_SIZE,
        )
        self.camera_focus_x = float(self.camera.camera.x)
        self.camera_focus_y = float(self.camera.camera.y)

        # Pulido: partículas, textos flotantes, hitstop
        self.fx = Particles()
        self.combat_visuals = CombatVisuals()
        self.environment = EnvironmentRenderer(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.texts = FloatTexts()
        self.hitstop_t = 0.0
        self.ambient_fx_t = 0.0
        self.ambient_audio_t = 2.0
        self.execution_cue_t = 0.0
        self._go_sound = False
        self._apply_accessibility_settings()
        # Sprites procedurales (caché por tipo)
        self.sprite_frames = {}
        for cls in CHARACTER_CLASSES:
            self.sprite_frames[('player', cls)] = load_player_frames(cls, make_player_frames)
        for et in ENEMY_STATS:
            self.sprite_frames[('enemy', et)] = load_entity_frames(
                'enemy', et, make_enemy_frames)
        for mid, base in (('colossal_slime', 'slime'), ('broken_knight', 'skeleton')):
            self.sprite_frames[('miniboss', mid)] = load_entity_frames(
                'miniboss', mid, make_enemy_frames, base)
        for bid in ('sanctum_guardian', 'cavern_mother', 'void_heart'):
            self.sprite_frames[('boss', bid)] = load_entity_frames(
                'boss', bid, make_boss_frames)
        self.art_assets = load_art_assets()
        self.ui.set_art_assets(self.sprite_frames, self.art_assets)
        # Música adaptativa (tolerante si falla el mixer)
        self.music = None
        self.combat_timer = 0.0
        if AdaptiveMusic is not None:
            try:
                self.music = AdaptiveMusic()
            except Exception:
                self.music = None
        self._apply_audio_settings()

        self.screen_state = GameScreen.CLASS_MENU
        self.selected_class = 'warrior'
        self.running = True

        self.player = None
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.drops = []  # [{'item': dict, 'rect': Rect, 'vy': float, 'gold': int}]
        self.inv_message = ""
        self.inv_message_t = 0.0
        self.current_zone = None
        self.current_room = None
        self.room_transition_t = 0.0
        self.zone_banner = ""
        self.zone_banner_t = 0.0
        self.gate_prompt = ""
        self.save_exists = PLAYER_SAVE_PATH.exists()
        # Jefe
        self.boss = None
        self.projectiles = pygame.sprite.Group()
        self.hazards = []  # [{'x','y','radius','damage','t','duration'}] veneno etc.
        self.death_visuals = []
        # Hechizos del jugador
        self.ally_shots = pygame.sprite.Group()
        self.pending_meteors = []  # [{'x','y','t','damage'}]
        self.blizzards = []  # [{'x','y','t','duration','tick'}]
        self.orb_angle = 0.0
        # Ataques cargados y direccionales de todas las clases.
        self.charging = 0.0
        self.charge_notified = False
        self.charge_variant = 'neutral'
        self.boss_banner_t = 0.0
        self.boss_phase_t = 0.0
        self.boss_phase_text = ""
        self.boss_phase_color = (255, 255, 255)
        self.victory_t = 0.0
        self.victory_text = ""
        self.boss_intro_t = 0.0
        self.boss_defeat_t = 0.0
        self.pending_boss_defeat = None
        self.boss_reward_altar = None
        # Intro e historia (solo partida nueva)
        self.intro_page = 0
        # Tutorial: cartel cercano
        self.sign_text = ""
        # Viaje rápido
        # Bestiario
        self.bestiary_tab = 'common'
        self.map_selected_zone = None
        # Pausa y reasignación de teclas
        self.rebinding = None  # acción en espera de tecla
        self.settings_tab = 'graphics'
        # Marca de muerte (rogue, click derecho)
        self.mark_cd = 0.0
        # Tienda
        self.shop_stock = []
        self.shop_level = 0
        self.shop_prompt = ""
        self.shop_tab = 'buy'  # buy | upgrade | craft
        self.dialogue_pages = []
        self.dialogue_page = 0
        self.dialogue_started_at = 0
        self.dialogue_quest_id = None
        self.dialogue_action = None
        self.dialogue_npc_id = None
        self.dialogue_choices = []
        self.dialogue_choice = 0
        self.active_secret_challenge = None
        self.secret_retry_t = 0.0
        self.active_room_encounter = None
        self.route_prompt = ''

    # --- Setup ---
    def run(self):
        while self.running:
            raw_dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            if self.hitstop_t > 0:
                # Hitstop: congelar el mundo un instante (pero seguir dibujando)
                self.hitstop_t -= raw_dt
            else:
                self.update(raw_dt)
            self._update_music(raw_dt)
            self.draw()
            self._present()
        if self.player:
            self.player.save_game()
        if self.music is not None:
            try:
                self.music.stop()
            except Exception:
                pass
        pygame.quit()

    def _apply_display_settings(self):
        size = tuple(self.settings['resolution'])
        flags = pygame.FULLSCREEN if self.settings['fullscreen'] else 0
        try:
            self.window = pygame.display.set_mode(size, flags)
        except pygame.error:
            self.settings['fullscreen'] = False
            self.settings['resolution'] = [SCREEN_WIDTH, SCREEN_HEIGHT]
            settings.save(self.settings)
            size = (SCREEN_WIDTH, SCREEN_HEIGHT)
            self.window = pygame.display.set_mode(size)
        window_width, window_height = self.window.get_size()
        scale = min(window_width / SCREEN_WIDTH, window_height / SCREEN_HEIGHT)
        width = max(1, int(SCREEN_WIDTH * scale))
        height = max(1, int(SCREEN_HEIGHT * scale))
        self._viewport = pygame.Rect((window_width - width) // 2,
                                     (window_height - height) // 2, width, height)

    def _apply_audio_settings(self):
        audio.set_volume(self.settings['master_volume'], self.settings['sfx_volume'])
        if self.music is not None:
            self.music.set_volume(self.settings['master_volume'], self.settings['music_volume'])

    def _apply_accessibility_settings(self):
        large = self.settings.get('text_size', 'normal') == 'large'
        self.font_small = pygame.font.Font(None, 20 if large else 18)
        self.font = pygame.font.Font(None, 24 if large else 22)
        self.font_big = pygame.font.Font(None, 38 if large else 36)
        self.font_title = pygame.font.Font(None, 48)
        if hasattr(self, 'ui'):
            self.ui.font_small = self.font_small
            self.ui.font = self.font
            self.ui.font_big = self.font_big
            self.ui.font_title = self.font_title
            self.ui.set_accessibility(self.settings.get('high_contrast', False))
        if hasattr(self, 'camera'):
            self.camera.trauma_scale = float(self.settings.get('screen_shake', 1.0))
            if self.camera.trauma_scale == 0:
                self.camera.trauma = 0.0
        if hasattr(self, 'fx'):
            self.fx.set_reduced_motion(self.settings.get('reduced_motion', False))

    def _present(self):
        self.window.fill((0, 0, 0))
        if self._viewport.size == self.screen.get_size():
            frame = self.screen
        else:
            frame = pygame.transform.smoothscale(self.screen, self._viewport.size)
        self.window.blit(frame, self._viewport.topleft)
        pygame.display.flip()

    def _logical_mouse_pos(self):
        x, y = pygame.mouse.get_pos()
        if not self._viewport.collidepoint(x, y):
            return (-1, -1)
        return (
            int((x - self._viewport.x) * SCREEN_WIDTH / self._viewport.width),
            int((y - self._viewport.y) * SCREEN_HEIGHT / self._viewport.height),
        )
