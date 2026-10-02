"""World coordinates stay independent from the tilted presentation and window size."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
WIDTH, HEIGHT = 1400, 800
WORLD_W, WORLD_H = 2000, 1400
TILT = 0.80
FPS = 60
ACCENT = (104, 224, 205)
AMBER = (242, 185, 92)
RED = (240, 100, 94)
TEXT = (235, 232, 220)
MUTED = (143, 158, 160)
PANEL = (15, 25, 31)
RESOLUTIONS = [(1280, 720), (1400, 800), (1600, 900), (1920, 1080)]
DIFFICULTIES = {'Recruit': .70, 'Regular': 1.0, 'Veteran': 1.35}
DEFAULT_SETTINGS = {
    'resolution': [1400, 800], 'fullscreen': False,
    'quality': 'High', 'shake': True,
    'master': .75, 'music': .30, 'sfx': .80,
    'sensitivity': 1.0, 'difficulty': 'Regular',
}

