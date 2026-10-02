import random

UPGRADES={
    'damage':('STOPPING POWER','Weapon damage +12%','DMG'),
    'fire_rate':('RAPID RESPONSE','Fire rate +10%','RPM'),
    'health':('FIELD MEDIC','Maximum health +60; heal 90','HP'),
    'speed':('LIGHT FOOTPRINT','Movement speed +8%','MOV'),
    'reload':('QUICK HANDS','Reload speed +15%','RLD'),
    'armor':('REINFORCED PLATES','Refill 75 armor','ARM'),
}


class WaveManager:
    def __init__(self,mode='operation'):
        self.mode=mode
        self.number=0
        self.pending=[]
        self.phase='intro'
        self.timer=0
        self.spawn_timer=0
        self.choices=[]

    def begin(self,game,number):
        self.number=number
        self.phase='intro'
        self.timer=3.0
        self.spawn_timer=.3
        amount=4+number*2
        if game.difficulty_factor<1:
            amount=max(4,amount-2)
        pool=['soldier','soldier','shotgun','sniper']
        if number>=2:
            pool+=['runner']
        if number>=4:
            pool+=['heavy']
        self.pending=[game.rng.choice(pool) for _ in range(min(45,amount))]
        if number%5==0:
            self.pending.insert(0,'boss')
        self.choices=[]
        game.announce(f'WAVE {number:02d}', 'BOSS CONTACT' if number%5==0 else 'HOSTILES INBOUND')

    def update(self,dt,game):
        if self.phase=='intro':
            self.timer=max(0,self.timer-dt)
            if self.timer==0:
                self.phase='combat'
            return
        if self.phase!='combat':
            return
        self.spawn_timer-=dt
        if self.pending and self.spawn_timer<=0 and len(game.enemies)<min(28,10+self.number):
            game.spawn_enemy(self.pending.pop(0))
            self.spawn_timer=max(.38,1.15-self.number*.052)
        if not self.pending and not game.enemies:
            bonus=500+self.number*50
            game.stats['score']+=bonus
            game.notify(f'+{bonus}  WAVE SECURED',color='accent')
            if self.mode=='operation' and self.number>=10:
                self.phase='complete'
                game.finish(True)
                return
            self.phase='intermission'
            self.choices=game.rng.sample(list(UPGRADES),3)
            for weapon in game.player.weapons:
                weapon.refill()
            game.player.health=min(game.player.max_health,game.player.health+45)
            game.player.armor=min(game.player.max_armor,game.player.armor+25)
            game.bullets.clear()
            game.pickups.clear()
            game.change_state('upgrade')
            game.audio.pause(True)
            game.save_checkpoint()

    def apply_upgrade(self,game,key=None):
        p=game.player
        if key=='damage':
            p.damage=min(3,p.damage*1.12)
        elif key=='fire_rate':
            p.fire_rate=min(2.2,p.fire_rate*1.1)
        elif key=='health':
            p.max_health=min(1400,p.max_health+60)
            p.health=min(p.max_health,p.health+90)
        elif key=='speed':
            p.speed_bonus=min(1.6,p.speed_bonus*1.08)
        elif key=='reload':
            p.reload_speed=min(2.6,p.reload_speed*1.15)
        elif key=='armor':
            p.armor=p.max_armor
        game.state='playing'
        game.audio.pause(False)
        self.begin(game,self.number+1)
        game.save_checkpoint()

    def snapshot(self):
        return {'mode':self.mode,'number':self.number,'pending':self.pending,
                'phase':self.phase,'timer':self.timer,'spawn_timer':self.spawn_timer,'choices':self.choices}
