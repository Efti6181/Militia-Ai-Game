# Upgrade notes

## Original project analysis

The supplied project was one 287-line script. It opened a 1400 × 800 arena with six obstacles, a mouse-aimed player with 500 HP, continuous shooting, three enemy archetypes, a score and R-to-restart. Graphics were loaded unconditionally from six external PNG paths. No corresponding image files were attached.

Important defects found:

1. `ShotgunBot` passed an integer rather than an `(x, y)` pair to `get_rect(center=...)`, so its first spawn could raise an exception.
2. The player rebuilt its rectangle after rotating, changing the collision footprint with aim angle.
3. Movement and projectiles depended on render frequency and integer rectangle truncation.
4. Shotgun and sniper bots lacked regular wall handling, while regular bots could stick against cover.
5. Fast bullets used frame-overlap collision and could skip a thin wall or enemy.
6. Multiple bullets hitting in one frame only called damage once per enemy in the group-collision loop.
7. Restart kept the old player's position and input/cooldown state rather than creating a fresh run.
8. The absence of any one required image prevented startup.
9. There was no pause, reload, settings, checkpoint or completion state.

## Preserved foundation

The upgrade preserves top-down arena survival, free directional movement, mouse aiming, held-button shooting, enemy projectiles, solid cover, 500 starting health, the three original bot archetypes, kill scoring and retry. The six original obstacles retain their relative arrangement, scaled into a larger arena.

Endless Survival carries the original survival premise forward. Operation: Iron Veil adds a finite ten-wave objective and victory screen. Ammo, armor, upgrades and the new enemy types extend the rules; they are intentional additions requested in the attached upgrade brief. Weapon and scoring values are rebalanced rather than pretending the new weapons share the original single-bullet damage.

## Implementation decisions

- Retain Python and Pygame using the compatible `pygame-ce` package. Use tilted 2.5D rendering and raised geometry; no engine migration or claim of true 3D.
- Use continuous world-space positions, a fixed 120 Hz simulation and a presentation loop capped at 60 FPS.
- Sweep projectile line segments and select the nearest wall or actor intersection. Also test the path from the player's body to the muzzle so firing into cover cannot spawn a bullet on the other side.
- Use static spatial buckets for obstacles and rebuilt agent buckets for collision and crowd steering.
- Use clearance-grid A* plus line-of-sight, preferred ranges, strafing, stagger, low-health cover and telegraphed sniper shots.
- Cache procedural art, font rendering, rotations, glow masks and UI panels. Cap particles at 650, bodies at 40 and floating labels at 60.
- Use a logical 1400 × 800 canvas with aspect-preserving letterboxing and inverse mouse projection.
- Generate playable default graphics and audio, while supporting cached optional sprite, animation and sound replacements.
- Save validated JSON to a writable user directory with an atomic replacement; avoid hardcoded paths or credentials.

## Boundaries

The visuals are stylized procedural art, not photorealistic assets. There is no network multiplayer, physical jumping, destructible cover or 3D mesh rendering. A moving mouse controls screen aim directly; sensitivity is exposed honestly as aim-rotation response. Hardware fullscreen and physical audio output still need checking on the player's own PC.
