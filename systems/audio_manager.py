from array import array
import math
import random
import pygame
from config import ASSETS


class AudioManager:
    """Optional file overrides and synthesized fallback audio; no NumPy dependency."""
    def __init__(self, settings):
        self.settings=settings
        self.sounds={}
        self.enabled=False
        self.paused=False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050,size=-16,channels=1,buffer=512)
            pygame.mixer.set_num_channels(24)
            pygame.mixer.set_reserved(1)
            self.music_channel=pygame.mixer.Channel(0)
            self.enabled=True
            for name in ('pistol','rifle','shotgun','sniper','reload','impact','hurt','kill','explosion','menu','dodge','victory','game_over'):
                self.sounds[name]=self.load(name) or self.synthesize(name)
            self.ambient=self.load('ambient',music=True) or self.synthesize('ambient')
            self.music_channel.play(self.ambient,loops=-1)
            self.apply(settings)
        except (pygame.error,OSError,ValueError):
            self.enabled=False

    def load(self,name,music=False):
        for ext in ('ogg','wav','mp3'):
            path=ASSETS/('music' if music else 'sounds')/f'{name}.{ext}'
            if path.is_file():
                try:
                    return pygame.mixer.Sound(str(path))
                except (pygame.error,OSError):
                    continue
        return None

    def synthesize(self,name):
        rng=random.Random(name)
        rate=pygame.mixer.get_init()[0]
        channels=pygame.mixer.get_init()[2]
        duration=4 if name=='ambient' else .5 if name in ('explosion','victory','game_over') else .13
        buffer=array('h')
        for i in range(int(rate*duration)):
            t=i/rate
            fade=max(0,1-t/duration)
            noise=rng.uniform(-1,1)
            if name=='ambient':
                # Integer-cycle frequencies give a seamless four-second loop.
                signal=.11*math.sin(t*2*math.pi*55)+.035*math.sin(t*2*math.pi*82.5)
                signal+=.02*math.sin(t*2*math.pi*110)*(.5+.5*math.sin(t*2*math.pi*.5))
            elif name in ('pistol','rifle','shotgun','sniper','explosion'):
                freq={'pistol':150,'rifle':110,'shotgun':65,'sniper':80,'explosion':42}[name]
                signal=(noise*.55+math.sin(2*math.pi*freq*t)*.4)*math.exp(-t*(13 if name=='explosion' else 38))
            elif name in ('victory','game_over'):
                freq=(330+int(t/.16)*110) if name=='victory' else (220-int(t/.16)*40)
                signal=.25*math.sin(t*2*math.pi*freq)*fade
            else:
                freq={'menu':620,'reload':230,'impact':500,'hurt':125,'kill':760,'dodge':95}[name]
                signal=(math.sin(2*math.pi*freq*t)*.20+noise*.08)*fade**3
            value=max(-32767,min(32767,int(signal*18000)))
            for _ in range(channels):
                buffer.append(value)
        return pygame.mixer.Sound(buffer=buffer.tobytes())

    def apply(self,settings):
        self.settings=settings
        if self.enabled:
            self.music_channel.set_volume(settings['master']*settings['music']*(.45 if self.paused else 1))

    def play(self,name,volume=1):
        if not self.enabled or name not in self.sounds:
            return
        try:
            channel=pygame.mixer.find_channel()
            if channel:
                channel.set_volume(self.settings['master']*self.settings['sfx']*volume)
                channel.play(self.sounds[name])
        except pygame.error:
            pass

    def pause(self,paused):
        if self.enabled:
            # Freeze transient effects with the simulation; keep ambient music quiet.
            for i in range(1,24):
                channel=pygame.mixer.Channel(i)
                channel.pause() if paused else channel.unpause()
            self.music_channel.set_volume(self.settings['master']*self.settings['music']*(.45 if paused else 1))
        self.paused=paused
