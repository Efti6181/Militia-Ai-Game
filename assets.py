from collections import OrderedDict
import math
import pygame
from config import ASSETS, WIDTH, HEIGHT, TILT, ACCENT, AMBER, RED, TEXT
from systems.animation_manager import AnimationManager


class ArtPen:
    """Draw source art at 3x resolution for smooth rotation and large menu portraits."""
    def __init__(self,surface):
        self.surface=surface
        self.scale=3

    def point(self,p):
        return tuple(round(v*self.scale) for v in p)

    def rect(self,color,rect,width=0,border_radius=0):
        pygame.draw.rect(self.surface,color,self.point(rect),width*self.scale,border_radius=border_radius*self.scale)

    def ellipse(self,color,rect,width=0):
        pygame.draw.ellipse(self.surface,color,self.point(rect),width*self.scale)

    def line(self,color,a,b,width=1):
        pygame.draw.line(self.surface,color,self.point(a),self.point(b),width*self.scale)

    def circle(self,color,point,radius):
        pygame.draw.circle(self.surface,color,self.point(point),radius*self.scale)

    def arc(self,color,rect,a,b,width=1):
        pygame.draw.arc(self.surface,color,self.point(rect),a,b,width*self.scale)


class Assets:
    """Cached procedural art, fonts and rotations; optional drop-in sprite overrides."""
    def __init__(self):
        self.fonts, self.actors, self.rotations, self.glows = {}, {}, {}, {}
        self.animations=AnimationManager(ASSETS/'images')
        self.text_cache = OrderedDict()
        self.vignette = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        for i in range(0,170,3):
            alpha=int(50*(1-i/170)**2)
            pygame.draw.rect(self.vignette,(3,9,15,alpha),(i,i,WIDTH-i*2,HEIGHT-i*2),3)
        self.damage = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        for i in range(0,100,3):
            pygame.draw.rect(self.damage,(195,35,34,int(85*(1-i/100))),(i,i,WIDTH-i*2,HEIGHT-i*2),3)
        self.menu_shade=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        for x in range(WIDTH):
            a = int(238 - 162*min(1, max(0,(x-220)/980)))
            pygame.draw.line(self.menu_shade,(5,14,22,a),(x,0),(x,HEIGHT))

    def font(self, size, kind='interface'):
        key=(size,kind)
        if key not in self.fonts:
            filename={'interface':'Interface.ttf','heading':'Heading.ttf','mono':'Telemetry.ttf'}[kind]
            path=ASSETS/'fonts'/filename
            try:
                self.fonts[key]=pygame.font.Font(str(path),size)
            except (OSError,pygame.error):
                self.fonts[key]=pygame.font.SysFont('dejavusans',size,bold=kind=='heading')
        return self.fonts[key]

    def text(self, value, size=18, color=TEXT, kind='interface'):
        key=(str(value),size,tuple(color),kind)
        if key not in self.text_cache:
            self.text_cache[key]=self.font(size,kind).render(str(value),True,color)
            if len(self.text_cache)>512:
                self.text_cache.popitem(last=False)
        else:
            self.text_cache.move_to_end(key)
        return self.text_cache[key]

    def glow(self, radius, color, additive=False):
        key=(radius,tuple(color),additive)
        if key not in self.glows:
            surf=pygame.Surface((radius*2+2,radius*2+2),pygame.SRCALPHA)
            for r in range(radius,0,-2):
                strength=(1-r/radius)**1.8
                a=int(90*strength)
                rgb=tuple(int(c*strength*.60) for c in color) if additive else color
                pygame.draw.circle(surf,(*rgb,a),(radius+1,radius+1),r)
            self.glows[key]=surf
        return self.glows[key]

    def actor_base(self, kind, weapon):
        key=kind,weapon
        if key in self.actors:
            return self.actors[key]
        for filename in (f'{kind}_{weapon}.png',f'{kind}.png'):
            path=ASSETS/'images'/filename
            if path.is_file():
                try:
                    img=pygame.image.load(str(path)).convert_alpha()
                    self.actors[key]=pygame.transform.smoothscale(img,(258,258))
                    return self.actors[key]
                except (OSError,pygame.error):
                    pass
        s=pygame.Surface((258,258),pygame.SRCALPHA)
        pen=ArtPen(s)
        c={'player':(70,122,121),'soldier':(130,76,64),'shotgun':(149,103,62),
           'sniper':(99,102,78),'runner':(139,80,80),'heavy':(112,98,85),'boss':(149,94,53)}[kind]
        trim=ACCENT if kind=='player' else RED if kind in ('soldier','runner') else AMBER
        # Boots, armor panels, shoulder pads, backpack, helmet and visor.
        pen.rect((16,23,25),(25,18,14,14),border_radius=4)
        pen.rect((16,23,25),(25,53,14,14),border_radius=4)
        pen.rect((31,41,42),(20,28,13,31),border_radius=5)
        pen.rect(tuple(max(0,v-22) for v in c),(27,25,24,37),border_radius=9)
        pen.rect(c,(31,28,21,31),border_radius=6)
        pen.line(tuple(min(255,v+33) for v in c),(32,30),(46,30),2)
        for y in (34,44,53):
            pen.rect((32,44,45),(29,y,10,5),border_radius=1)
        for y in (20,58):
            pen.rect(c,(40,y,15,10),border_radius=4)
            pen.line(trim,(44,y+2),(52,y+2),2)
        pen.line((38,48,47),(48,28),(61,35),8)
        pen.line((38,48,47),(48,60),(60,51),8)
        lengths={'pistol':18,'rifle':29,'shotgun':27,'sniper':34}
        length=lengths.get(weapon,29)
        pen.rect((17,25,29),(48,39,length,7),border_radius=1)
        pen.rect((91,106,107),(55,39,length-8,2))
        pen.rect((37,46,49),(56,43,8,9),border_radius=2)
        if weapon=='sniper':
            pen.rect((20,29,31),(52,34,18,5),border_radius=2)
            pen.circle(ACCENT,(69,36),2)
        pen.ellipse((20,31,34),(36,29,23,28))
        pen.ellipse(tuple(min(255,v+22) for v in c),(37,29,20,25))
        pen.arc(tuple(min(255,v+64) for v in c),(39,31,15,21),.7,3.1,2)
        pen.rect((16,29,33),(51,35,7,13),border_radius=2)
        pen.line(trim,(55,36),(55,44),2)
        if kind in ('heavy','boss'):
            pen.rect((39,45,46),(31,24,9,40),2,border_radius=2)
        self.actors[key]=s
        return s

    def actor(self, kind, angle, weapon='rifle', scale=1, motion='idle', phase=0):
        angle=int(round(angle/5)*5)%360
        animation=self.animations.frame(kind,motion,phase)
        index=animation[0] if animation else -1
        key=kind,angle,weapon,scale,motion if animation else '',index
        if key not in self.rotations:
            source=animation[1] if animation else self.actor_base(kind,weapon)
            img=pygame.transform.rotate(source,-angle)
            img=pygame.transform.smoothscale(img,(max(1,int(img.get_width()*scale/3)),
                                                  max(1,int(img.get_height()*TILT*scale/3))))
            self.rotations[key]=img
        return self.rotations[key]

    def gun_icon(self, surf, position, weapon, color=TEXT, scale=1):
        x,y=position
        length={'pistol':26,'rifle':53,'shotgun':48,'sniper':64}[weapon]*scale
        pygame.draw.rect(surf,color,(x,y,length,5*scale),border_radius=2)
        pygame.draw.polygon(surf,color,[(x+9*scale,y),(x+20*scale,y),
                                      (x+17*scale,y+14*scale),(x+9*scale,y+14*scale)])
        if weapon!='pistol':
            pygame.draw.line(surf,color,(x-8*scale,y+3*scale),(x,y+3*scale),6)
        if weapon=='sniper':
            pygame.draw.rect(surf,color,(x+17*scale,y-7*scale,19*scale,4*scale),border_radius=1)
