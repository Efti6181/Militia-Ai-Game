from dataclasses import dataclass
import pygame
from bullet import Bullet


@dataclass(frozen=True)
class WeaponSpec:
    key: str
    title: str
    label: str
    damage: float
    interval: float
    magazine: int
    reserve: int
    reload: float
    speed: float
    spread: float
    recoil: float
    pellets: int=1
    life: float=1.65


SPECS=[
    WeaponSpec('pistol','P9 / SIDEARM','Precise. Reliable. Unlimited reserve.',42,.27,14,84,1.05,1200,1.1,3),
    WeaponSpec('rifle','AR-30 / ASSAULT','Balanced automatic fire.',30,.105,30,180,1.55,1450,2.1,4),
    WeaponSpec('shotgun','SG-8 / BREACHER','Eight pellets. Close-range power.',23,.73,8,48,1.9,1030,11,12,8,.62),
    WeaponSpec('sniper','SR-5 / MARKSMAN','Center hits earn a precision bonus.',180,1.04,5,30,2.25,2100,.25,15,1,1.8),
]


class Weapon:
    def __init__(self,spec):
        self.spec=spec
        self.ammo=spec.magazine
        self.reserve=spec.reserve
        self.cooldown=0
        self.reload_left=0
        self.reload_duration=spec.reload

    @property
    def reloading(self):
        return self.reload_left>0

    def reload(self,speed=1):
        if self.reloading or self.ammo>=self.spec.magazine or (self.reserve<=0 and self.spec.key!='pistol'):
            return False
        self.reload_duration=self.spec.reload/speed
        self.reload_left=self.reload_duration
        return True

    def update(self,dt):
        self.cooldown=max(0,self.cooldown-dt)
        if self.reload_left>0:
            self.reload_left=max(0,self.reload_left-dt)
            if self.reload_left==0:
                amount=self.spec.magazine-self.ammo
                if self.spec.key!='pistol':
                    amount=min(amount,self.reserve)
                    self.reserve-=amount
                self.ammo+=amount

    def fire(self,pos,angle,rng,shot_id,damage=1,fire_rate=1,movement=0):
        if self.cooldown>0 or self.reloading or self.ammo<=0:
            return []
        self.ammo-=1
        self.cooldown=self.spec.interval/fire_rate
        out=[]
        spread=self.spec.spread*(1+movement*.55)
        for i in range(self.spec.pellets):
            deviation=rng.uniform(-spread,spread)
            if self.spec.pellets>1:
                deviation=(i-(self.spec.pellets-1)/2)*spread/4+rng.uniform(-1,1)
            velocity=pygame.Vector2(self.spec.speed,0).rotate(angle+deviation)
            out.append(Bullet(pygame.Vector2(pos),velocity,'player',self.spec.damage*damage,
                              self.spec.life,self.spec.key=='sniper',shot_id))
        return out

    def refill(self):
        self.ammo=self.spec.magazine
        self.reserve=self.spec.reserve
        self.reload_left=0

    def snapshot(self):
        return {'ammo':self.ammo,'reserve':self.reserve,'reload_left':self.reload_left,
                'reload_duration':self.reload_duration,'cooldown':self.cooldown}

