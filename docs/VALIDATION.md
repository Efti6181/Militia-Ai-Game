# Validation record

Verified on 2026-10-01 with Python 3.12.14 and pygame-ce 2.5.8.

## Behavioral checks

All **30 tests passed** in `python -m unittest discover -s tests -v`. The exact output is in `test_results.txt`.

Coverage includes preserved health and enemy archetypes, fixed-step movement at 30/60/120 render FPS, diagonal normalization, circle/wall and player/enemy collision, rotation-invariant hitboxes, sprint/dodge stamina, all four weapons, reload cancellation, blocked muzzle paths, swept bullet collision, nearest-wall blocking, per-shot shotgun accuracy, sniper warning, low-health cover, A* routing, paused clocks, upgrade/refill transitions, final-wave victory, endless wave 11, defeat/retry, checkpoint round-trips, malformed save handling, settings persistence, coordinate mapping, menu events, every screen's render/bounds, unavailable audio behavior and optional animation fallback.

## Actual render and integration checks

- The menu and game launch through both `main.py` and the `militia.py` compatibility entry point, including launch from another working directory.
- Actual Pygame frames for menu, deployment, controls, settings, combat, reloading, pause, upgrades, defeat and victory were generated and visually inspected. Preview battle statistics and result screens are staged for illustration.
- A live stress scene began with 24 enemies, including all six types, with real AI, projectiles, particles, HUD and display rendering. Agent/world clearance, player/world clearance, particle bounds and accuracy bounds stayed valid. The harness player was invulnerable so performance measurement could continue.
- A separate normal-damage simulation with a stationary, non-firing player reached the real game-over state after 27.4 seconds against wave 1.
- Default art and synthesized audio worked without the six original PNGs or external audio files.

## Performance sample

The 360 measured frames after warm-up used SDL dummy video/audio drivers, a 1400 × 800 software-rendered canvas, High effects and a 120 Hz simulation.

| Measurement | Result |
|---|---:|
| Average update + draw + display time | 5.554 ms |
| 95th percentile frame time | 6.990 ms |
| Equivalent uncapped throughput | 180.1 FPS |
| Normal presentation cap | 60 FPS |

Raw measurements are in `benchmark.json`. This container result is not a hardware FPS guarantee. Native Windows fullscreen behavior, physical sound output and subjective mouse feel need checking on the player's own machine; they were not manually tested on that machine.
