from dataclasses import dataclass
import math
import random
import pygame
from config import WORLD_W, WORLD_H, TILT
from bullet import segment_rect
from systems.navigation import Navigation


@dataclass
class Obstacle:
    rect: pygame.Rect
    height: int
    kind: str
    label: str = ''


class SpatialHash:
    def __init__(self, cell=128):
        self.cell = cell
        self.buckets = {}

    def cells(self, rect):
        for y in range(math.floor(rect.top / self.cell), math.floor(rect.bottom / self.cell) + 1):
            for x in range(math.floor(rect.left / self.cell), math.floor(rect.right / self.cell) + 1):
                yield x, y

    def add(self, obj, rect):
        for key in self.cells(rect):
            self.buckets.setdefault(key, []).append(obj)

    def query(self, rect):
        seen = set()
        for key in self.cells(rect):
            for obj in self.buckets.get(key, ()):
                if id(obj) not in seen:
                    seen.add(id(obj))
                    yield obj


class World:
    def __init__(self, fonts):
        # The six cover pieces preserve the relative layout of militia.py.
        sx, sy = WORLD_W / 1400, WORLD_H / 800
        original = [(200, 600, 150, 25), (900, 520, 300, 25), (200, 350, 200, 25),
                    (950, 250, 200, 25), (620, 450, 50, 100), (1200, 450, 30, 150)]
        self.obstacles = [Obstacle(pygame.Rect(x*sx, y*sy, w*sx, h*sy), 33, 'barrier')
                          for x, y, w, h in original]
        self.obstacles += [
            Obstacle(pygame.Rect(130, 110, 330, 180), 92, 'building', '01 / COMMS'),
            Obstacle(pygame.Rect(1250, 115, 400, 160), 74, 'building', '02 / DEPOT'),
            Obstacle(pygame.Rect(90, 1030, 195, 190), 64, 'container', 'C-07'),
            Obstacle(pygame.Rect(1685, 1025, 195, 180), 64, 'container', 'C-12'),
            Obstacle(pygame.Rect(570, 310, 96, 75), 32, 'crate'),
            Obstacle(pygame.Rect(680, 345, 70, 55), 28, 'crate'),
            Obstacle(pygame.Rect(1380, 820, 85, 78), 38, 'crate'),
            Obstacle(pygame.Rect(735, 1005, 88, 80), 32, 'crate'),
            Obstacle(pygame.Rect(1595, 410, 80, 160), 28, 'vehicle'),
            Obstacle(pygame.Rect(415, 1045, 140, 65), 24, 'vehicle'),
        ]
        self.spatial = SpatialHash()
        for o in self.obstacles:
            self.spatial.add(o, o.rect.inflate(100, 100))
        self.nav = Navigation(self.obstacles)
        self.lamps = [(495, 200), (1180, 195), (1720, 625), (560, 930), (1510, 1120)]
        self.floor = self.make_floor(fonts)

    def nearby(self, pos, radius):
        return self.spatial.query(pygame.Rect(pos.x-radius, pos.y-radius, radius*2, radius*2))

    def free(self, pos, radius=24):
        if not (radius + 20 <= pos[0] <= WORLD_W-radius-20 and
                radius+20 <= pos[1] <= WORLD_H-radius-20):
            return False
        p = pygame.Vector2(pos)
        for o in self.nearby(p, radius):
            nearest = pygame.Vector2(max(o.rect.left, min(o.rect.right, p.x)),
                                     max(o.rect.top, min(o.rect.bottom, p.y)))
            if nearest.distance_squared_to(p) <= radius * radius:
                return False
        return True

    def resolve(self, pos, radius):
        p = pygame.Vector2(pos)
        for _ in range(3):
            for o in self.nearby(p, radius+2):
                r = o.rect
                near = pygame.Vector2(max(r.left, min(r.right, p.x)), max(r.top, min(r.bottom, p.y)))
                delta = p - near
                distance = delta.length()
                if distance < radius:
                    if distance > .0001:
                        p += delta * ((radius - distance + .01) / distance)
                    else:
                        edges = [(p.x-r.left, (-1, 0)), (r.right-p.x, (1, 0)),
                                 (p.y-r.top, (0, -1)), (r.bottom-p.y, (0, 1))]
                        dist, direction = min(edges, key=lambda item: item[0])
                        p += pygame.Vector2(direction) * (dist + radius + .01)
        p.x = max(radius+20, min(WORLD_W-radius-20, p.x))
        p.y = max(radius+20, min(WORLD_H-radius-20, p.y))
        return p

    def move(self, pos, delta, radius):
        steps = max(1, math.ceil(delta.length() / max(5, radius*.6)))
        result = pygame.Vector2(pos)
        for _ in range(steps):
            result = self.resolve(result + delta / steps, radius)
        return result

    def clear_line(self, a, b, padding=0):
        bounds = pygame.Rect(min(a.x, b.x)-padding, min(a.y, b.y)-padding,
                             abs(a.x-b.x)+padding*2+1, abs(a.y-b.y)+padding*2+1)
        return not any(segment_rect(a, b, o.rect.inflate(padding*2, padding*2)) is not None
                       for o in self.spatial.query(bounds))

    def spawn_point(self, rng, player, occupied=(), radius=24):
        candidates = []
        for _ in range(100):
            edge = rng.randrange(4)
            p = pygame.Vector2(rng.uniform(70, WORLD_W-70), rng.uniform(70, WORLD_H-70))
            if edge < 2:
                p.x = 65 if edge == 0 else WORLD_W-65
            else:
                p.y = 65 if edge == 2 else WORLD_H-65
            if self.free(p, radius) and all(p.distance_to(e.pos) > radius+e.radius+8 for e in occupied):
                candidates.append(p)
                if p.distance_to(player) > 620:
                    return p
        if candidates:
            return max(candidates, key=lambda p: p.distance_squared_to(player))
        return pygame.Vector2(1000, 80)

    def cover_point(self, enemy, target):
        choices = []
        for o in self.obstacles:
            away = pygame.Vector2(o.rect.center) - target
            if away.length_squared() < 1:
                continue
            away.normalize_ip()
            point = pygame.Vector2(o.rect.center) + away * (max(o.rect.size)*.62 + enemy.radius+28)
            if self.free(point, enemy.radius) and not self.clear_line(point, target):
                choices.append(point)
        return min(choices, key=lambda p: p.distance_squared_to(enemy.pos)) if choices else enemy.pos.copy()

    def make_floor(self, fonts):
        floor = pygame.Surface((WORLD_W, int(WORLD_H*TILT))).convert()
        rng = random.Random(928)
        for y in range(floor.get_height()):
            t = y/floor.get_height()
            pygame.draw.line(floor, (int(48+10*t), int(58+7*t), int(58+5*t)), (0,y),(WORLD_W,y))
        def rect(color, xywh, width=0):
            x,y,w,h=xywh
            pygame.draw.rect(floor,color,(x,int(y*TILT),w,max(1,int(h*TILT))),width)
        rect((37,46,48),(775,0,450,WORLD_H))
        rect((40,49,49),(0,605,WORLD_W,260))
        for x in (776,1223):
            pygame.draw.line(floor,(83,89,79),(x,0),(x,int(WORLD_H*TILT)),2)
        for y in (607,863):
            pygame.draw.line(floor,(82,88,79),(0,int(y*TILT)),(WORLD_W,int(y*TILT)),2)
        for y in range(50,WORLD_H,110):
            rect((131,126,99),(990,y,5,52))
        for x in range(40,WORLD_W,110):
            rect((124,122,97),(x,733,52,4))
        # Concrete slabs and worn parking paint around the combat lanes.
        for y in range(0,WORLD_H,175):
            for x in range(0,WORLD_W,180):
                if 760 < x < 1200 or 580 < y < 850:
                    continue
                rect((66,76,70),(x+3,y+3,174,168),1)
        for _ in range(13000):
            x,y=rng.randrange(WORLD_W),rng.randrange(floor.get_height())
            base = floor.get_at((x,y))
            delta=rng.randrange(-6,7)
            floor.set_at((x,y),tuple(max(0,min(255,c+delta)) for c in base[:3]))
        for _ in range(230):
            x,y=rng.randrange(35,WORLD_W-35),rng.randrange(35,floor.get_height()-35)
            pygame.draw.line(floor,(53,61,57),(x,y),(x+rng.randrange(-14,15),y+rng.randrange(-6,7)),1)
        for _ in range(85):
            x,y=rng.randrange(WORLD_W),rng.randrange(floor.get_height())
            pygame.draw.circle(floor,(77,79,62),(x,y),rng.randrange(1,4))
        # Cracked asphalt, tire tracks, drains, discarded casing piles and perimeter scrub.
        for x in (902,916,1060,1074):
            for y in range(370,565,10):
                rect((29,37,39),(x,y,4,6))
        for x,y in ((740,590),(1245,874),(1110,210),(585,975)):
            rect((25,37,37),(x,y,40,17))
            for offset in range(5,37,6):
                rect((67,76,65),(x+offset,y+2,2,13))
        for x,y in ((1018,916),(700,660),(1440,727),(364,889)):
            for _ in range(18):
                q=(x+rng.randrange(-27,28),int((y+rng.randrange(-18,19))*TILT))
                pygame.draw.line(floor,(149,134,80),q,(q[0]+4,q[1]+2),1)
        for _ in range(55):
            x=rng.choice([rng.randrange(45,80),rng.randrange(WORLD_W-85,WORLD_W-40)])
            y=rng.randrange(40,WORLD_H-40)
            for _ in range(4):
                q=(x+rng.randrange(-10,11),int(y*TILT)+rng.randrange(-7,8))
                pygame.draw.circle(floor,rng.choice([(60,79,57),(68,83,58),(81,89,62)]),q,rng.randrange(2,7))
        for o in self.obstacles:
            r=o.rect
            # Projected directional ground shadows are cached with the environment.
            shadow=pygame.Surface((r.width+60,int(r.height*TILT)+60),pygame.SRCALPHA)
            pygame.draw.rect(shadow,(5,12,16,90),shadow.get_rect(),border_radius=6)
            floor.blit(shadow,(r.x+18,int(r.y*TILT)+12))
            if o.kind == 'building':
                rect((106,100,74),(r.x-8,r.y-8,r.w+16,r.h+16),2)
        for x,y in self.lamps:
            glow=pygame.Surface((230,180),pygame.SRCALPHA)
            for rad in range(85,0,-5):
                pygame.draw.ellipse(glow,(183,150,80,int(11*(1-rad/90))),(115-rad,90-rad*.75,rad*2,rad*1.5))
            floor.blit(glow,(x-115,int(y*TILT)-90))
        for point,label in [((112,565),'SECTOR A'),((1450,955),'SECTOR C'),((836,1100),'EXTRACTION'),((830,100),'NORTH GATE')]:
            text=fonts.font(23,'heading').render(label,True,(103,111,91))
            floor.blit(text,(point[0],int(point[1]*TILT)))
        for y in range(40,WORLD_H,45):
            for x in (22,WORLD_W-22):
                pygame.draw.line(floor,(106,117,102),(x,int(y*TILT)),(x,int((y+22)*TILT)),3)
        for x in range(30,WORLD_W,45):
            for y in (24,int((WORLD_H-24)*TILT)):
                pygame.draw.line(floor,(103,113,101),(x,y),(x+24,y),3)
        return floor
