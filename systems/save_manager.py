import copy
import json
import math
import os
from pathlib import Path
from config import DEFAULT_SETTINGS, DIFFICULTIES, RESOLUTIONS


def number(value, default, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(low, min(high, value)) if math.isfinite(value) else default


def clean_settings(raw):
    out = copy.deepcopy(DEFAULT_SETTINGS)
    if not isinstance(raw, dict):
        return out
    if isinstance(raw.get('resolution'), (list, tuple)):
        if tuple(raw['resolution']) in RESOLUTIONS:
            out['resolution'] = list(raw['resolution'])
    for key in ('fullscreen', 'shake'):
        if isinstance(raw.get(key), bool):
            out[key] = raw[key]
    for key in ('master', 'music', 'sfx'):
        out[key] = number(raw.get(key), out[key], 0, 1)
    out['sensitivity'] = number(raw.get('sensitivity'), 1.0, .4, 2)
    if raw.get('quality') in ('Low', 'High'):
        out['quality'] = raw['quality']
    if raw.get('difficulty') in DIFFICULTIES:
        out['difficulty'] = raw['difficulty']
    return out


class SaveManager:
    """Atomic saves in a writable per-user directory, with safe corrupt-file fallback."""
    def __init__(self, directory=None):
        base = os.environ.get('LOCALAPPDATA') or os.environ.get('XDG_DATA_HOME')
        default = Path(base) / 'AI_Militia' if base else Path.home() / '.ai_militia'
        self.directory = Path(directory) if directory else default
        self.path = self.directory / 'save.json'
        self.warning = ''
        self.data = {'version': 1, 'settings': copy.deepcopy(DEFAULT_SETTINGS),
                     'high_score': 0, 'checkpoint': None, 'completed_missions': 0}
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(raw, dict) or raw.get('version') != 1:
                raise ValueError('Unsupported save format')
            self.data['settings'] = clean_settings(raw.get('settings'))
            self.data['high_score'] = int(number(raw.get('high_score'), 0, 0, 10**10))
            self.data['completed_missions'] = int(number(raw.get('completed_missions'), 0, 0, 100000))
            if isinstance(raw.get('checkpoint'), dict):
                self.data['checkpoint'] = raw['checkpoint']
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError):
            self.warning = 'Save unreadable. Defaults restored.'

    @property
    def settings(self):
        return self.data['settings']

    def write(self):
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix('.tmp')
            temp.write_text(json.dumps(self.data, indent=2, allow_nan=False), encoding='utf-8')
            temp.replace(self.path)
            self.warning = ''
            return True
        except (OSError, ValueError, TypeError):
            self.warning = 'Could not save progress in this folder.'
            return False

    def checkpoint(self, snapshot):
        self.data['checkpoint'] = snapshot
        return self.write()

    def finish(self, score, victory=False):
        self.data['high_score'] = max(self.data['high_score'], int(score))
        self.data['checkpoint'] = None
        if victory:
            self.data['completed_missions'] += 1
        return self.write()

