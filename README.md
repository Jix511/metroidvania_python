# Metroidvania Python

Videojuego metroidvania 2D desarrollado con Python y Pygame como proyecto de
Estructuras de Datos y Algoritmos. Incluye exploracion por zonas, combate,
habilidades, inventario, misiones, jefes, puntos de control y persistencia de
partidas mediante JSON.

## Caracteristicas

- Exploracion de un mundo dividido en zonas y habitaciones.
- Combate contra enemigos, minijefes y jefes con diferentes patrones.
- Clases de personaje, habilidades, hechizos y variantes de ataque.
- Inventario, equipamiento, economia y mejoras.
- Misiones, dialogos, secretos, logros y bestiario.
- Puntos de control, viaje rapido y progreso persistente.
- Pruebas automatizadas con `unittest`.

## Requisitos

- Python 3
- Pygame

## Instalacion

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Ejecucion

```powershell
python main.py
```

## Controles principales

| Accion | Teclas |
| --- | --- |
| Moverse | `A`, `D` o flechas |
| Saltar | `W` o flecha arriba |
| Atacar | `Espacio` |
| Dash o rodada | `Shift` |
| Parada | `Z` |
| Pocion | `Q` |
| Habilidades | `K` o `Tab` |
| Inventario | `I` |
| Mapa | `H` |
| Viaje rapido | `M` |
| Bestiario | `J` |
| Misiones | `U` |

Los controles pueden reasignarse desde la configuracion del juego.

## Pruebas

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

## Estructura

- `core/`: coordinacion y ciclo principal del juego.
- `entities/`: jugador, enemigos y jefes.
- `world/`: mapa, camara, zonas y mecanismos.
- `systems/`: habilidades, objetos, audio, misiones y persistencia.
- `presentation/`: interfaz, animaciones y efectos visuales.
- `data/`: configuracion y contenido en archivos JSON.
- `tests/`: pruebas automatizadas.

