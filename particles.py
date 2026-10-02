from dataclasses import dataclass
import math
import pygame
from config import ACCENT, AMBER


@dataclass
class Particle:
    pos: pygame.Vector2
    velocity: pygame.Vector2
    color: tuple
    life: float
    total: float
    size: float
    height: float = 12
    rise: float = 0
    kind: str = 'spark'


class Particles:
    def __init__(self, rng):
        self.items=[]
        self.rng=rng

    def burst(self,pos,color=AMBER,count=12,power=120,kind='spark',quality='High'):
        count=count if quality=='High' else max(2,count//3)
        for _ in range(count):
            if len(self.items)>=650:
                break
            a=self.rng.uniform(0,360)
            velocity=pygame.Vector2(self.rng.uniform(power*.2,power),0).rotate(a)
            life=self.rng.uniform(.2,.55) if kind=='spark' else self.rng.uniform(.55,1.3)
            self.items.append(Particle(pygame.Vector2(pos),velocity,color,life,life,
                                       self.rng.uniform(1.3,3.8) if kind=='spark' else self.rng.uniform(8,15),
                                       14,self.rng.uniform(0,20) if kind=='smoke' else self.rng.uniform(25,80),kind))

    def update(self,dt):
        for p in self.items:
            p.life-=dt
            p.pos+=p.velocity*dt
            p.velocity*=math.exp(-4*dt)
            p.height=max(0,p.height+p.rise*dt)
            if p.kind=='spark':
                p.rise-=220*dt
        self.items=[p for p in self.items if p.life>0]

    def draw(self,surf,camera,assets,quality):
        for p in self.items:
            q=camera.project(p.pos,p.height)
            if not (-40<q.x<surf.get_width()+40 and -40<q.y<surf.get_height()+40):
                continue
            life=p.life/p.total
            if p.kind=='smoke':
                radius=int(p.size*(1.6-life*.6))
                smoke=assets.glow(radius,p.color)
                smoke.set_alpha(int(life*85))
                surf.blit(smoke,(q.x-radius,q.y-radius))
            else:
                if quality=='High' and p.size>2.8:
                    glow=assets.glow(12,p.color,True)
                    surf.blit(glow,(q.x-12,q.y-12),special_flags=pygame.BLEND_RGB_ADD)
                color=tuple(int(c*(.3+.7*life)) for c in p.color)
                end=q-p.velocity*.012
                pygame.draw.line(surf,color,q,end,max(1,int(p.size*life)))
