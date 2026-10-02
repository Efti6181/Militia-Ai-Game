from dataclasses import dataclass
import math
import pygame
from bullet import Bullet


@dataclass(frozen=True)
class EnemySpec:
    health: float
    speed: float
    radius: int
    preferred_range: int
    interval: float
    damage: float
    score: int
    weapon: str


ENEMIES={
    'soldier':EnemySpec(90,130,20,355,1.28,20,100,'rifle'),
    'shotgun':EnemySpec(150,117,22,180,2.15,9,160,'shotgun'),
    'sniper':EnemySpec(240,82,20,690,3.2,46,220,'sniper'),
    'runner':EnemySpec(65,228,18,95,1.05,16,120,'pistol'),
    'heavy':EnemySpec(340,83,27,350,.28,16,300,'rifle'),
    'boss':EnemySpec(1850,77,37,390,1.12,24,1500,'rifle'),
}


class Enemy:
    def __init__(self,kind,pos,wave,rng):
        self.kind=kind
        self.spec=ENEMIES[kind]
        self.pos=pygame.Vector2(pos)
        self.radius=self.spec.radius
        self.max_health=self.spec.health*(1+max(0,wave-1)*.045)
        self.health=self.max_health
        self.angle=90
        self.state='PATROL'
        self.cooldown=rng.uniform(.8,1.8)
        self.path_timer=rng.uniform(0,.4)
        self.route=[]
        self.hit_flash=0
        self.stagger=0
        self.knockback=pygame.Vector2()
        self.flash=0
        self.walk_time=rng.uniform(0,6)
        self.strafe=1 if rng.random()<.5 else -1
        self.telegraph=0
        self.aim_direction=pygame.Vector2(0,1)
        self.contact_cooldown=0
        self.age=0
        self.cover_left=0
        self.cover_target=None
        self.has_retreated=False
        self.wave=wave

    def take_damage(self,damage,direction):
        self.health=max(0,self.health-damage)
        self.hit_flash=.14
        self.stagger=.10 if self.kind not in ('heavy','boss') else .035
        if direction.length_squared()>0:
            self.knockback=direction.normalize()*(28 if self.kind in ('heavy','boss') else 115)
        if self.health==0:
            self.state='DEAD'
            return True
        return False

    def update(self,dt,game):
        if self.health<=0:
            return
        self.age+=dt
        self.pos=game.world.move(self.pos,self.knockback*dt,self.radius)
        self.knockback*=math.exp(-13*dt)
        for key in ('hit_flash','stagger','flash','contact_cooldown'):
            setattr(self,key,max(0,getattr(self,key)-dt))
        self.cooldown=max(0,self.cooldown-dt)
        self.path_timer-=dt
        self.cover_left=max(0,self.cover_left-dt)
        player=game.player
        toward=player.pos-self.pos
        distance=max(.1,toward.length())
        direction=toward/distance
        visible=game.world.clear_line(self.pos,player.pos)
        desired=self.spec.preferred_range
        goal=player.pos.copy()
        self.angle=math.degrees(math.atan2(direction.y,direction.x))
        if self.telegraph>0:
            self.state='ATTACK'
            self.telegraph=max(0,self.telegraph-dt)
            if self.telegraph==0:
                self.shoot(game,self.aim_direction)
            return
        movement=pygame.Vector2()
        if self.age<.5:
            self.state='PATROL'
        elif self.cover_left>0 and self.cover_target is not None:
            self.state='TAKE_COVER'
            goal=self.cover_target
            if self.pos.distance_to(goal)<32:
                self.state='RETREAT'
                movement=pygame.Vector2()
            else:
                movement=goal-self.pos
        elif self.health/self.max_health<.27 and not self.has_retreated and self.kind not in ('runner','boss'):
            self.has_retreated=True
            self.cover_left=2.3
            self.cover_target=game.world.cover_point(self,player.pos)
            self.state='TAKE_COVER'
            goal=self.cover_target
            movement=goal-self.pos
        elif not visible or distance>desired*1.13:
            self.state='CHASE'
            movement=direction
        elif distance<desired*.65 and self.kind!='runner':
            self.state='RETREAT'
            movement=-direction+pygame.Vector2(-direction.y,direction.x)*self.strafe*.35
            goal=self.pos+movement*180
        else:
            self.state='ATTACK'
            movement=pygame.Vector2(-direction.y,direction.x)*self.strafe*.40
            goal=self.pos+movement*100
        if movement.length_squared()>0 and self.stagger<=0:
            if not game.world.clear_line(self.pos,goal,self.radius+4):
                if self.path_timer<=0 or not self.route:
                    self.route=game.world.nav.path(self.pos,goal)
                    self.path_timer=game.rng.uniform(.55,.95)
                while self.route and self.pos.distance_to(self.route[0])<20:
                    self.route.pop(0)
                movement=(self.route[0]-self.pos) if self.route else pygame.Vector2()
            else:
                self.route=[]
            if movement.length_squared()>0:
                # Separate nearby agents without introducing O(n^2) crowd checks.
                steering=pygame.Vector2()
                area=pygame.Rect(self.pos.x-72,self.pos.y-72,144,144)
                for other in game.enemy_spatial.query(area):
                    if other is self:
                        continue
                    diff=self.pos-other.pos
                    dist=diff.length()
                    if .1<dist<self.radius+other.radius+15:
                        steering+=diff/dist*.65
                movement=movement.normalize()+steering
                if movement.length_squared()>0:
                    movement.normalize_ip()
                    speed=self.spec.speed*(1+min(12,self.wave)*.015)
                    self.pos=game.world.move(self.pos,movement*speed*dt,self.radius)
                    self.walk_time+=speed*dt*.025
        if visible and distance<desired*1.5 and self.cooldown<=0 and self.state not in ('TAKE_COVER','PATROL','RETREAT'):
            if self.kind=='sniper':
                self.telegraph=.95
                self.aim_direction=direction.copy()
                self.cooldown=self.spec.interval
            else:
                self.shoot(game,direction)
        if distance<self.radius+player.radius+4:
            if self.contact_cooldown==0:
                game.damage_player(14 if self.kind!='boss' else 30,self.pos)
                self.contact_cooldown=.65
            self.pos=game.world.resolve(self.pos-direction*5,self.radius)

    def shoot(self,game,direction):
        if direction.length_squared()<.01:
            return
        base=math.degrees(math.atan2(direction.y,direction.x))
        count=8 if self.kind=='shotgun' else 9 if self.kind=='boss' else 1
        damage=self.spec.damage*game.difficulty_factor
        for i in range(count):
            spread=(i-(count-1)/2)*(4.6 if self.kind=='shotgun' else 11) if count>1 else game.rng.uniform(-3.5,3.5)
            speed=690 if self.kind!='sniper' else 1300
            game.bullets.append(Bullet(self.pos.copy(),pygame.Vector2(speed,0).rotate(base+spread),'enemy',damage,
                                       1.0 if self.kind=='shotgun' else 2.5))
        self.cooldown=self.spec.interval/(1+min(12,self.wave)*.014)
        self.flash=.065
        game.audio.play(self.spec.weapon,.20 if self.kind!='boss' else .55)

    def snapshot(self):
        return {'kind':self.kind,'pos':list(self.pos),'health':self.health,'max_health':self.max_health,
                'cooldown':self.cooldown,'age':self.age,'has_retreated':self.has_retreated,'wave':self.wave}
