# Arquitectura

El punto de entrada es `main.py`. La clase `core.game.Game` conserva únicamente
la inicialización y el bucle principal; el comportamiento se compone mediante
mixins pequeños y especializados.

## Paquetes

- `core/`: coordinación de partida, eventos, combate, hechizos, jefes,
  economía, actualización, renderizado, música y rutas del proyecto.
- `entities/`: jugador, enemigos y jefes.
- `world/`: mapa, cámara, zonas, puertas y checkpoints.
- `systems/`: habilidades, objetos, estados, controles, audio, música,
  hechizos, bestiario y persistencia JSON.
- `presentation/`: interfaz, sprites procedurales y efectos visuales.
- `assets/`: recursos generados o distribuidos con el juego.
- `data/`: estadísticas, balance y definición del mundo editables en JSON.
- `saves/`: partidas y configuración persistente.

## Responsabilidades de `core`

- `game.py`: construcción de `Game` y bucle principal.
- `game_state.py`: nueva partida, carga, respawn, viaje y NG+.
- `game_events.py`: entrada y navegación de interfaces.
- `game_update.py`: actualización general y cámara.
- `game_render.py`: dibujo del mundo y selección de animaciones.
- `game_combat.py`: daño, ataques y recompensas por enemigos.
- `game_spells.py`: magia y ataques a distancia.
- `game_bosses.py`: aparición, actualización y recompensas de jefes.
- `game_economy.py`: botín, tienda, mejoras y forja.
- `game_audio.py`: selección de música adaptativa.
- `game_data.py`: datos estáticos de encuentros y progresión.
- `screen_state.py`: estado único de la pantalla activa y transiciones.
- `paths.py`: rutas absolutas de recursos y guardados.

## Regla de dependencias

Los módulos deben importar por paquete completo, por ejemplo
`from systems.items import generate_item`. Los módulos de dominio no deben
importar `core.game`; reciben el estado compartido mediante la instancia de
`Game` y sus mixins.

Las pantallas son mutuamente excluyentes y se representan con `GameScreen`.
Para cambiar de menú o volver al juego se utiliza `set_screen(...)`; no deben
añadirse nuevas banderas booleanas `show_*`.

`systems.settings` valida y persiste resolución, modo de pantalla y volúmenes
en `saves/settings.json`. El juego siempre dibuja en un lienzo lógico de
960×640 y `core.game` lo escala con bandas laterales cuando la ventana usa otra
proporción, manteniendo alineados la interfaz y el ratón.

Los JSON persistentes se escriben mediante `systems.json_storage`. Esta capa
realiza reemplazos atómicos, valida los datos y mantiene archivos `*.backup.json`.
La compatibilidad entre versiones de partida vive en `systems.save_schema`.

Los datos de enemigos, élites, minijefes y jefes se cargan desde `data/` por
medio de `systems.balance_data`. Objetos, rarezas, economía y kits iniciales se
validan en `systems.item_data`; los árboles y requisitos de habilidades se
validan en `systems.skill_data`. La lógica ejecutable permanece en Python,
mientras los valores de balance y progresión viven en JSON.

Cada enemigo común declara percepción, límite territorial, memoria y cadencia
de ataque en `data/enemies.json`. `entities.enemy.Enemy` usa esos parámetros
para alternar patrulla, alerta, persecución, aviso, ataque, defensa y retirada.
Los slimes saltan, los esqueletos bloquean golpes frontales, los murciélagos
atacan en picado y los goblins alternan embestidas con retirada. El daño por
contacto solo se aplica durante ventanas de ataque, y enemigos cercanos
comparten alertas sin abandonar indefinidamente su territorio.

Las cadenas de combate de las cuatro clases viven en `data/combos.json` y se
validan mediante `systems.combo_data`. El jugador mantiene pasos y ventanas
separadas para suelo y aire. Guerrero y rogue terminan la cadena terrestre con
lanzamiento y la aérea con golpe descendente y rebote; maga y arquera cambian
cadencia, daño y cantidad de proyectiles. Un dash puede cancelar la recuperación
sin perder inmediatamente la ventana de continuación.

La geometría, zonas, puertas, checkpoints, carteles, encuentros y recompensas
fijas del mapa viven en `data/world.json`. `world.world_data` carga y valida
esas referencias antes de que `world.tilemap` construya el escenario.

El mundo se divide en cinco salas contiguas de 60 tiles, equivalentes al ancho
lógico de la pantalla. Los límites usan puertas y muros locales, nunca columnas
de altura completa. La migración de guardado 13 traslada posiciones del mapa
antiguo a la misma zona relativa del mapa ampliado.

El mapa interactivo reutiliza esas definiciones y guarda `explored_zones` en
la partida. Solo muestra detalles de zonas visitadas; los santuarios activos
permiten viaje directo desde el mapa y las partidas antiguas descubren su zona
actual durante la migración.

Los secretos se describen en `data/secrets.json` y se validan mediante
`systems.secret_data`. Cada zona contiene una pared falsa y un cofre; algunas
recompensas exigen superar una prueba de combate con tiempo limitado.
`core.game_exploration.GameExplorationMixin` coordina descubrimiento, pruebas y
entrega de recompensas. El mapa muestra el progreso por zona y el guardado
conserva paredes descubiertas y cofres abiertos.

`systems.rewards` centraliza la entrega de XP, oro, puntos de habilidad,
curación y objetos. Acepta recompensas definidas por otros sistemas y carga los
paquetes reutilizables desde `data/rewards.json`; enemigos, minijefes y jefes
usan la misma API, que devuelve un resultado apto para mensajes y efectos.

Los emisores visuales se definen en `data/effects.json` y se validan mediante
`presentation.effect_data`. `presentation.fx.Particles` mantiene un pool de
objetos `Particle`, soporta formas y capas y conserva `burst`/`trail` para
compatibilidad. Las entidades vivas heredan de `entities.base.CombatEntity`,
que concentra animación, proporción de vida y feedback de estados.

Los jefes declaran tres fases en `data/bosses.json`, incluyendo mensaje, color y
patrón de entrada. Al cruzar un umbral entran brevemente en transición, limpian
proyectiles y peligros anteriores y anuncian el nuevo patrón. Las entradas
pueden invocar esbirros, lanzar una onda radial, crear una zona peligrosa o
iniciar un ataque meteoro; el resto del comportamiento continúa usando el
ajuste de velocidad, daño y enfriamientos de cada fase.

Las hojas de sprites externas se describen en `data/sprite_sheets.json`.
`presentation.sprite_loader` corta cuadrículas incluso cuando sus dimensiones
no son divisibles exactamente, recorta transparencia, normaliza el anclaje por
los pies y conserva los sprites procedurales como fallback. Todos los protagonistas
usan escalado por vecino cercano para conservar el pixel art.

Los cuatro protagonistas comparten ahora ese contrato visual y técnico:
guerrero y rogue masculinos, maga y arquera femeninas, todos con hojas 4×4 y
animaciones de reposo, carrera, salto, daño y ataque.

El lienzo de jugador mide 80×56: el cuerpo conserva su escala original, mientras
el ancho transparente evita recortar espadas, arcos, flechas o bastones durante
los fotogramas de ataque. La colisión continúa usando el rectángulo físico de la
entidad y no el tamaño visual.

## Dirección artística

Los recursos visuales de ejecución se organizan como atlas transparentes bajo
`assets/sprites`: protagonistas individuales; familias de enemigos, minijefes
y jefes; el herrero y los iconos de equipo en `support-atlas.png`; y materiales
para los cinco biomas en `world/biome-atlas.png`.

Cada combatiente externo conserva un fallback procedural. Las nuevas hojas
deben mirar a la derecha, alinear los pies con el borde inferior de la celda,
usar transparencia real, escalado por vecino cercano, grupos de píxeles
nítidos y siluetas legibles al tamaño real de juego.

`presentation.combat_visuals` añade feedback transitorio en coordenadas del
mundo sin participar en colisiones ni daño. Guerrero, rogue, maga y arquera
poseen firmas visuales distintas. `Player.begin_action` desacopla el recorrido
de fotogramas del cooldown, de modo que ataques y hechizos muestran preparación,
impacto y recuperación sin modificar el balance.

`presentation.environment.EnvironmentRenderer` dibuja siluetas de fondo con
parallax y clima por bioma antes y después del mundo físico. Su carga visual se
controla mediante `effects_quality` en los ajustes persistentes. El mapa conserva
la responsabilidad exclusiva sobre tiles, puertas, decoración y colisiones.

La pestaña de accesibilidad persiste tamaño de texto, alto contraste, movimiento
reducido, intensidad de sacudida y reducción de destellos. El juego aplica los
cambios en tiempo real: reconstruye fuentes, refuerza fondos del HUD, escala la
cámara, reduce partículas y ambiente dinámico, y evita el flash blanco de las
entidades cuando corresponde. Las configuraciones antiguas reciben valores
predeterminados durante la normalización.

## Narrativa y misiones

Las misiones viven en `data/quests.json` y son validadas por
`systems.quest_data`. `core.game_narrative.GameNarrativeMixin` coordina las
conversaciones, la aceptación, la entrega y las recompensas mediante la API
común de `systems.rewards`.

Los habitantes se definen en `data/npcs.json` y se validan en
`systems.npc_data`. Maela, Ilyra, Caldus y Sira ocupan zonas diferentes,
reaccionan a los jefes derrotados y ofrecen opciones de conversación. Cada
misión declara su `giver`, de modo que el recorrido narrativo queda distribuido
por el mundo mientras Maela conserva la función exclusiva de comerciante.

El diario se abre con `U` y presenta bloqueos, progreso y recompensas. El estado
de cada misión y el historial de objetos recogidos se conservan en el guardado,
por lo que vender o equipar un objeto de misión no impide completarla después.

## Simulador de balance

`tools.balance_simulator` analiza combate, XP, oro, objetos y árboles sin abrir
Pygame. Ejemplos:

```powershell
python -m tools.balance_simulator --level 5 --ng 0
python -m tools.balance_simulator --level 10 --ng 2 --format json --output reports/balance.json
```

Los parámetros permiten comparar distintos niveles y ciclos de Nuevo Juego+.
