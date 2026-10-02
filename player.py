import math
import pygame
from weapons import Weapon, SPECS


class Player:
    def __init__(self):
        self.pos=pygame.Vector2(1000,1230)
        self.velocity=pygame.Vector2()
        self.radius=19
        self.angle=-90
        self.health=self.max_health=500.0
        self.armor=self.max_armor=75.0
        self.stamina=100.0
        self.weapons=[Weapon(s) for s in SPECS]
        self.selected=1
        self.damage=1.0
        self.fire_rate=1.0
        self.reload_speed=1.0
        self.speed_bonus=1.0
        self.recoil=0
        self.flash=0
        self.hit_flash=0
        self.invulnerable=0
        self.dodge_left=0
        self.dodge_cooldown=0
        self.dodge_direction=pygame.Vector2(0,-1)
        self.walk_time=0
        self.sprinting=False
        self.exhausted=False
        self.last_damage_angle=0

    @property
    def weapon(self):
        return self.weapons[self.selected]

    def switch(self,index):
        # A holstered gun cannot finish its reload invisibly.
        if index!=self.selected:
            self.weapon.reload_left=0
        self.selected=index%len(self.weapons)

    def dodge(self,direction):
        if self.dodge_cooldown>0 or self.stamina<28:
            return False
        self.dodge_direction=direction.normalize() if direction.length_squared()>.01 else pygame.Vector2(1,0).rotate(self.angle)
        self.dodge_left=.20
        self.invulnerable=.20
        self.dodge_cooldown=.85
        self.stamina-=28
        return True

    def update(self,dt,movement,aim,sprint,world,sensitivity):
        for w in self.weapons:
            w.update(dt)
        for key in ('flash','hit_flash','invulnerable','dodge_left','dodge_cooldown'):
            setattr(self,key,max(0,getattr(self,key)-dt))
        self.recoil=max(0,self.recoil-dt*38)
        if self.stamina<=4:
            self.exhausted=True
        elif self.stamina>=22 or not sprint:
            self.exhausted=False
        self.sprinting=sprint and movement.length_squared()>0 and not self.exhausted and not self.weapon.reloading
        speed=315*self.speed_bonus*(1.5 if self.sprinting else 1)
        if movement.length_squared()>1:
            movement=movement.normalize()
        desired=movement*speed
        self.velocity=self.velocity.lerp(desired,1-math.exp(-20*dt))
        delta=self.dodge_direction*870*dt if self.dodge_left>0 else self.velocity*dt
        self.pos=world.move(self.pos,delta,self.radius)
        self.walk_time+=self.velocity.length()*dt*.028
        self.stamina=max(0,min(100,self.stamina+(-27 if self.sprinting else 22)*dt))
        direction=aim-self.pos
        if direction.length_squared()>2:
            target=math.degrees(math.atan2(direction.y,direction.x))
            turn=(target-self.angle+180)%360-180
            self.angle+=turn*(1-math.exp(-38*sensitivity*dt))

    def take_damage(self,amount,source):
        if self.invulnerable>0 or self.health<=0:
            return False
        blocked=min(self.armor,amount*.65)
        self.armor-=blocked
        self.health=max(0,self.health-(amount-blocked))
        self.hit_flash=.28
        direction=source-self.pos
        self.last_damage_angle=math.degrees(math.atan2(direction.y,direction.x))
        return True

    def snapshot(self):
        return {'pos':list(self.pos),'health':self.health,'max_health':self.max_health,
                'armor':self.armor,'stamina':self.stamina,'selected':self.selected,
                'damage':self.damage,'fire_rate':self.fire_rate,'reload_speed':self.reload_speed,
                'speed_bonus':self.speed_bonus,'weapons':[w.snapshot() for w in self.weapons]}
