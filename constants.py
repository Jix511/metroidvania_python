# constants.py - Configuración global del juego

# Configuración de pantalla
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
TILE_SIZE = 16  # Tamaño de cada bloque del mapa

# Colores (R, G, B)
COLORS = {
    'BLACK': (0, 0, 0),
    'WHITE': (255, 255, 255),
    'RED': (255, 0, 0),
    'GREEN': (0, 255, 0),
    'BLUE': (0, 0, 255),
    'YELLOW': (255, 255, 0),
    'PURPLE': (128, 0, 128),
    'ORANGE': (255, 165, 0),
    'GRAY': (100, 100, 100),
}

# Alias para conveniencia
GREEN = COLORS['GREEN']
BLUE = COLORS['BLUE']
RED = COLORS['RED']
YELLOW = COLORS['YELLOW']

# Configuración del jugador
PLAYER_START_POS = (TILE_SIZE * 10, TILE_SIZE * 10)
PLAYER_SPEED = 2
PLAYER_HEALTH = 100
PLAYER_DAMAGE = 10

# Configuración del juego - todo en unidades por segundo (dt independiente de FPS)
FPS = 60
GRAVITY = 2400.0  # px/s^2
JUMP_STRENGTH = -850.0  # px/s (~150px de altura: repisas a 112px cómodas)
MAX_FALL_SPEED = 1100.0  # px/s
ATTACK_COOLDOWN = 0.33  # segundos
INVINCIBLE_TIME = 0.75  # segundos
CAMERA_SMOOTH = 8.0  # factor lerp por segundo

# Tipos de personajes disponibles (para selección)
# speed en px/s (dt). Migración: saves viejos con speed<20 se multiplican x60 en load.
CHARACTER_CLASSES = {
    'warrior': {
        'name': 'Guerrero',
        'health': 100,
        'speed': 170.0,
        'damage': 15,
        'description': 'Fuerte en combate, pero lento',
        'starting_ability': 'golpe_cargado',
    },
    'rogue': {
        'name': 'Rogue',
        'health': 70,
        'speed': 250.0,
        'damage': 10,
        'description': 'Rápido y ágil, pero frágil',
        'starting_ability': 'esquiva',
    },
    'mage': {
        'name': 'Maga',
        'health': 50,
        'speed': 200.0,
        'damage': 20,
        'description': 'Ataques a distancia poderosos, vida baja',
        'starting_ability': 'barrera_magica',
    },
    'ranger': {
        'name': 'Arquera',
        'health': 65,
        'speed': 230.0,
        'damage': 12,
        'description': 'Flechazos precisos y móvil, frágil de cerca',
        'starting_ability': 'tiro_arco',
    },
    'kitsune': {
        'name': 'Kitsune',
        'health': 60,
        'speed': 240.0,
        'damage': 14,
        'description': 'Fuego espiritual, engaño y gran movilidad',
        'starting_ability': 'spirit_step',
    },
    'reaper': {
        'name': 'Segadora',
        'health': 75,
        'speed': 205.0,
        'damage': 17,
        'description': 'Guadaña, almas y control de grupos',
        'starting_ability': 'soul_reap',
    },
}
