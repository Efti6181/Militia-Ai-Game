from dataclasses import dataclass, field
import copy
import math
import os
import random
import pygame
from config import WIDTH,HEIGHT,WORLD_W,WORLD_H,FPS,TEXT,ACCENT,AMBER,RED,DIFFICULTIES,RESOLUTIONS,DEFAULT_SETTINGS
from assets import Assets
from player import Player
from enemy import Enemy,ENEMIES
from bullet import Bullet,segment_circle,segment_rect
from world import World,SpatialHash
from camera import Camera
from particles import Particles
from renderer import Renderer
from systems.save_manager import SaveManager,number,clean_settings
from systems.audio_manager import AudioManager
from systems.wave_manager import WaveManager,UPGRADES
from ui.interface import Interface


@dataclass
class InputFrame:
    movement: pygame.Vector2=field(default_factory=pygame.Vector2)
    aim: pygame.Vector2=field(default_factory=lambda:pygame.Vector2(1000,800))
    fire: bool=False
    sprint: bool=False


class Game:
    def __init__(self,headless=False,save_dir=None,seed=None):
        if headless:
            os.environ['SDL_VIDEODRIVER']='dummy'
            os.environ['SDL_AUDIODRIVER']='dummy'
        pygame.display.init()
        pygame.font.init()
        self.clock=pygame.time.Clock()
        self.save=SaveManager(save_dir)
        self.settings=self.save.settings
        self.headless=headless
        self.display=None
        self.viewport=pygame.Rect(0,0,WIDTH,HEIGHT)
        self.set_display()
        pygame.display.set_caption('AI Militia: Combat Zone | Iron Veil')
        self.canvas=pygame.Surface((WIDTH,HEIGHT)).convert()
        self.assets=Assets()
        self.world=World(self.assets)
        self.rng=random.Random(seed)
        self.fx_rng=random.Random(None if seed is None else seed+93)
        self.camera=Camera(self.fx_rng)
        self.particles=Particles(self.fx_rng)
        self.renderer=Renderer(self.assets)
        self.ui=Interface(self.assets)
        self.audio=AudioManager(self.settings)
        self.player=Player()
        self.enemies=[]
        self.bullets=[]
        self.corpses=[]
        self.pickups=[]
        self.floating=[]
        self.notifications=[]
        self.enemy_spatial=SpatialHash()
        self.wave=WaveManager()
        self.stats=self.empty_stats()
        self.state='menu'
        self.parent='menu'
        self.running=True
        self.has_run=False
        self.run_finished=False
        self.visual_time=0.0
        self.announcement=''
        self.announcement_sub=''
        self.announcement_left=0
        self.hit_marker=0
        self.critical_marker=False
        self.combo=0
        self.combo_left=0
        self.shot_counter=0
        self.hit_ids=set()
        self.input=InputFrame()
        self.difficulty_factor=1.0
        self.run_difficulty='Regular'
        self.accumulator=0
        self.auto_save=20
        self.transition=1.0
        self.mouse=pygame.Vector2(WIDTH/2,HEIGHT/2)
        self.last_dt=1/60
        icon=pygame.Surface((32,32),pygame.SRCALPHA)
        self.ui.logo(icon,(1,4),.7)
        pygame.display.set_icon(icon)

    @staticmethod
    def empty_stats():
        return {'score':0,'kills':0,'shots':0,'hits':0,'precision':0,'time':0.0}

    def set_display(self):
        size=tuple(self.settings['resolution'])
        flags=pygame.FULLSCREEN if self.settings['fullscreen'] and not self.headless else pygame.RESIZABLE
        try:
            self.display=pygame.display.set_mode(size,flags)
        except pygame.error:
            self.settings['fullscreen']=False
            self.display=pygame.display.set_mode((1280,720),pygame.RESIZABLE)
        self.resize_viewport(self.display.get_size())

    def resize_viewport(self,size):
        scale=min(size[0]/WIDTH,size[1]/HEIGHT)
        self.viewport=pygame.Rect(0,0,int(WIDTH*scale),int(HEIGHT*scale))
        self.viewport.center=(size[0]//2,size[1]//2)

    def logical_mouse(self,point):
        return pygame.Vector2((point[0]-self.viewport.x)*WIDTH/self.viewport.w,
                              (point[1]-self.viewport.y)*HEIGHT/self.viewport.h)

    def change_state(self,state):
        self.state=state
        self.transition=.35
        self.ui.buttons.clear()
        self.accumulator=0
        pygame.mouse.set_visible(state!='playing')

    def start(self,mode='operation'):
        self.player=Player()
        self.player.pos=self.world.resolve(self.player.pos,self.player.radius)
        self.enemies=[]
        self.bullets=[]
        self.corpses=[]
        self.pickups=[]
        self.floating=[]
        self.notifications=[]
        self.particles.items.clear()
        self.stats=self.empty_stats()
        self.ui.health_display=self.player.health
        self.ui.score_display=0
        self.combo=self.combo_left=self.hit_marker=0
        self.hit_ids.clear()
        self.shot_counter=0
        self.auto_save=20
        self.run_difficulty=self.settings['difficulty']
        self.difficulty_factor=DIFFICULTIES[self.run_difficulty]
        self.wave=WaveManager(mode)
        self.has_run=True
        self.run_finished=False
        self.audio.pause(False)
        self.change_state('playing')
        self.wave.begin(self,1)
        self.camera.follow(self.player.pos,self.player.pos,0,instant=True)
        self.input=InputFrame(aim=self.player.pos+pygame.Vector2(0,-200))
        self.save_checkpoint()

    def spawn_enemy(self,kind):
        radius=ENEMIES[kind].radius
        position=self.world.spawn_point(self.rng,self.player.pos,self.enemies,radius)
        self.enemies.append(Enemy(kind,position,self.wave.number,self.rng))
        self.particles.burst(position,RED,8,40,quality=self.settings['quality'])

    def announce(self,title,subtitle):
        self.announcement,self.announcement_sub=title,subtitle
        self.announcement_left=2.8

    def notify(self,text,color='amber'):
        self.notifications.append({'text':text,'life':3.0,'color':color})
        self.notifications=self.notifications[-5:]

    def damage_player(self,damage,source):
        if self.player.take_damage(damage,pygame.Vector2(source)):
            self.camera.kick(.18)
            self.audio.play('hurt',.75)
            self.particles.burst(self.player.pos,RED,8,80,quality=self.settings['quality'])

    def fire(self):
        p=self.player
        w=p.weapon
        if p.dodge_left>0 or p.sprinting or w.reloading:
            return
        if w.ammo==0:
            if w.reload(p.reload_speed):
                self.audio.play('reload')
            return
        direction=pygame.Vector2(1,0).rotate(p.angle)
        muzzle=p.pos+direction*38
        bullets=w.fire(muzzle,p.angle,self.rng,self.shot_counter+1,p.damage,p.fire_rate,p.velocity.length()/470+p.recoil/12)
        if not bullets:
            return
        self.shot_counter+=1
        self.stats['shots']+=1
        if self.shot_counter%100==0:
            self.hit_ids={i for i in self.hit_ids if i>self.shot_counter-1000}
        if self.world.clear_line(p.pos,muzzle):
            self.bullets.extend(bullets)
        else:
            # A barrel pressed into cover must not teleport a bullet through it.
            self.particles.burst(p.pos+direction*20,AMBER,7,110,quality=self.settings['quality'])
        p.flash=.065
        p.recoil=min(28,p.recoil+w.spec.recoil)
        p.velocity-=direction*min(18,w.spec.recoil*1.5)
        self.camera.kick(.10 if w.spec.key=='rifle' else .20 if w.spec.key=='pistol' else .40)
        self.audio.play(w.spec.key)
        self.particles.burst(muzzle,(105,107,99),2,18,'smoke',self.settings['quality'])

    def kill_enemy(self,enemy,precision=False):
        self.combo=self.combo+1 if self.combo_left>0 else 1
        self.combo_left=3.0
        multiplier=1+min(4,self.combo-1)*.1
        points=int(enemy.spec.score*multiplier)+(75 if precision else 0)
        self.stats['score']+=points
        self.stats['kills']+=1
        if precision:
            self.stats['precision']+=1
        text=f'+{points} '+('PRECISION' if precision else 'COMMANDER DOWN' if enemy.kind=='boss' else enemy.kind.upper())
        self.notify(text)
        self.floating.append({'pos':enemy.pos.copy(),'text':f'+{points}','life':1.2,'color':AMBER})
        self.corpses.append({'pos':enemy.pos.copy(),'kind':enemy.kind,'angle':enemy.angle+75,
                            'weapon':enemy.spec.weapon,'scale':1.7 if enemy.kind=='boss' else 1.2 if enemy.kind=='heavy' else 1,'life':12.0})
        self.corpses=self.corpses[-40:]
        self.particles.burst(enemy.pos,AMBER,25 if enemy.kind=='boss' else 14,200,quality=self.settings['quality'])
        self.particles.burst(enemy.pos,(126,128,112),14 if enemy.kind=='boss' else 5,48,'smoke',self.settings['quality'])
        self.audio.play('explosion' if enemy.kind=='boss' else 'kill',.8)
        if enemy.kind=='boss':
            self.camera.kick(.95)
        if self.rng.random()<.25 or enemy.kind=='boss':
            self.pickups.append({'pos':enemy.pos.copy(),'kind':'medkit' if self.rng.random()<.45 else 'ammo','life':18.0})

    def update_bullets(self,dt):
        alive=[]
        for bullet in self.bullets:
            bullet.step(dt)
            if bullet.life<=0 or not (-30<bullet.pos.x<WORLD_W+30 and -30<bullet.pos.y<WORLD_H+30):
                continue
            best_t=2.0
            hit=None
            area=pygame.Rect(min(bullet.prev.x,bullet.pos.x)-42,min(bullet.prev.y,bullet.pos.y)-42,
                             abs(bullet.prev.x-bullet.pos.x)+84,abs(bullet.prev.y-bullet.pos.y)+84)
            for wall in self.world.spatial.query(area):
                t=segment_rect(bullet.prev,bullet.pos,wall.rect)
                if t is not None and t<best_t:
                    best_t,hit=t,'wall'
            targets=self.enemy_spatial.query(area) if bullet.owner=='player' else [self.player]
            for target in targets:
                if target.health<=0:
                    continue
                t=segment_circle(bullet.prev,bullet.pos,target.pos,target.radius)
                if t is not None and t<best_t:
                    best_t,hit=t,target
            if hit is None:
                alive.append(bullet)
                continue
            point=bullet.prev.lerp(bullet.pos,best_t)
            self.particles.burst(point,AMBER if hit=='wall' else ACCENT if bullet.owner=='player' else RED,
                                 6,110,quality=self.settings['quality'])
            if hit=='wall':
                self.audio.play('impact',.12)
            elif bullet.owner=='enemy':
                self.damage_player(bullet.damage,bullet.prev)
            else:
                precision=False
                if bullet.critical:
                    # Check the full traveled line towards the enemy center, not just its near edge.
                    extended=bullet.pos+bullet.velocity.normalize()*hit.radius*2
                    precision=segment_circle(bullet.prev,extended,hit.pos,hit.radius*.38) is not None
                damage=bullet.damage*(1.4 if precision else 1)
                if bullet.shot_id not in self.hit_ids:
                    self.hit_ids.add(bullet.shot_id)
                    self.stats['hits']+=1
                self.hit_marker=.12
                self.critical_marker=precision
                self.audio.play('impact',.25)
                self.floating.append({'pos':hit.pos.copy(),'text':str(int(damage)),
                                      'life':.65,'color':AMBER if precision else ACCENT})
                if hit.take_damage(damage,bullet.velocity):
                    self.kill_enemy(hit,precision)
        self.bullets=alive
        self.enemies=[e for e in self.enemies if e.health>0]

    def resolve_actor_contacts(self):
        p=self.player
        if p.dodge_left>0:
            return
        area=pygame.Rect(p.pos.x-80,p.pos.y-80,160,160)
        for enemy in self.enemy_spatial.query(area):
            diff=p.pos-enemy.pos
            distance=diff.length()
            overlap=p.radius+enemy.radius-distance
            if overlap>0:
                direction=diff/distance if distance>.001 else pygame.Vector2(1,0)
                p.pos=self.world.resolve(p.pos+direction*(overlap*.55+.01),p.radius)
                enemy.pos=self.world.resolve(enemy.pos-direction*(overlap*.45+.01),enemy.radius)

    def step(self,dt,inputs):
        if self.state!='playing':
            return
        self.stats['time']+=dt
        p=self.player
        p.update(dt,inputs.movement,inputs.aim,inputs.sprint,self.world,self.settings['sensitivity'])
        if inputs.fire:
            self.fire()
        self.enemy_spatial=SpatialHash()
        for e in self.enemies:
            self.enemy_spatial.add(e,pygame.Rect(e.pos.x-e.radius,e.pos.y-e.radius,e.radius*2,e.radius*2))
        for e in self.enemies:
            e.update(dt,self)
        self.resolve_actor_contacts()
        # Rebuild after movement so fast targets remain in the correct collision bucket.
        self.enemy_spatial=SpatialHash()
        for e in self.enemies:
            self.enemy_spatial.add(e,pygame.Rect(e.pos.x-e.radius,e.pos.y-e.radius,e.radius*2,e.radius*2))
        self.update_bullets(dt)
        self.particles.update(dt)
        for item in self.corpses+self.floating+self.pickups+self.notifications:
            item['life']-=dt
        self.corpses=[x for x in self.corpses if x['life']>0]
        self.floating=[x for x in self.floating if x['life']>0][-60:]
        self.notifications=[x for x in self.notifications if x['life']>0]
        for pickup in self.pickups:
            if pickup['pos'].distance_to(p.pos)<35:
                if pickup['kind']=='medkit':
                    p.health=min(p.max_health,p.health+70)
                    self.notify('+70 FIELD MEDIC','accent')
                else:
                    for w in p.weapons:
                        w.reserve=min(w.spec.reserve*2,w.reserve+max(5,w.spec.magazine*2))
                    self.notify('AMMO RECOVERED','accent')
                pickup['life']=0
                self.audio.play('reload',.55)
        self.pickups=[x for x in self.pickups if x['life']>0]
        self.combo_left=max(0,self.combo_left-dt)
        self.hit_marker=max(0,self.hit_marker-dt)
        self.announcement_left=max(0,self.announcement_left-dt)
        self.camera.follow(p.pos,inputs.aim,dt,self.settings['shake'])
        if p.health<=0:
            self.finish(False)
            return
        self.wave.update(dt,self)
        self.auto_save-=dt
        if self.auto_save<=0 and self.state=='playing':
            self.save_checkpoint()
            self.auto_save=20

    def update(self,dt,inputs=None):
        self.last_dt=dt
        self.visual_time+=dt
        self.transition=max(0,self.transition-dt*2.5)
        if self.state=='playing':
            inputs=inputs or self.input
            self.accumulator+=min(dt,.1)
            while self.accumulator>=1/120 and self.state=='playing':
                self.step(1/120,inputs)
                self.accumulator-=1/120
            if self.state!='playing':
                self.accumulator=0
        elif self.state in ('menu','deploy','credits','controls','settings') and not self.has_run:
            # Flyover uses UI time; combat and weapon timers stay frozen in all menus.
            self.camera.center.update(1120+math.sin(self.visual_time*.075)*125,
                                      530+math.cos(self.visual_time*.08)*90)
            self.camera.offset.update(0,0)

    def pause(self):
        if self.state=='playing':
            self.change_state('pause')
            self.audio.pause(True)
            self.save_checkpoint()
        elif self.state=='pause':
            self.change_state('playing')
            self.audio.pause(False)

    def finish(self,victory):
        self.run_finished=True
        self.change_state('victory' if victory else 'game_over')
        self.audio.pause(True)
        self.audio.play('victory' if victory else 'game_over')
        self.save.finish(self.stats['score'],victory)

    def snapshot(self):
        return {'version':1,'player':self.player.snapshot(),'enemies':[e.snapshot() for e in self.enemies],
                'bullets':[{'pos':list(b.pos),'velocity':list(b.velocity),'owner':b.owner,'damage':b.damage,
                            'life':b.life,'critical':b.critical,'shot_id':b.shot_id} for b in self.bullets],
                'wave':self.wave.snapshot(),'stats':copy.deepcopy(self.stats),
                'difficulty':self.run_difficulty,'shot_counter':self.shot_counter,'hit_ids':sorted(self.hit_ids),
                'pickups':[{'pos':list(x['pos']),'kind':x['kind'],'life':x['life']} for x in self.pickups],
                'combo':self.combo,'combo_left':self.combo_left}

    def save_checkpoint(self):
        if self.has_run and not self.run_finished:
            self.save.data['high_score']=max(self.save.data['high_score'],self.stats['score'])
            return self.save.checkpoint(self.snapshot())
        return False

    def restore(self):
        snap=self.save.data.get('checkpoint')
        try:
            if not isinstance(snap,dict) or snap.get('version')!=1:
                raise ValueError('Unsupported checkpoint')
            p=snap['player']
            wave=snap['wave']
            if not isinstance(p,dict) or not isinstance(wave,dict) or wave.get('mode') not in ('operation','survival'):
                raise ValueError('Invalid checkpoint')
            def vec(raw):
                if not isinstance(raw,list) or len(raw)!=2:
                    raise ValueError('Invalid position')
                return pygame.Vector2(number(raw[0],1000,0,WORLD_W),number(raw[1],700,0,WORLD_H))
            def val(data,key,default,low,high):
                return number(data.get(key),default,low,high)
            player=Player()
            player.pos=self.world.resolve(vec(p['pos']),player.radius)
            player.max_health=val(p,'max_health',500,500,1400)
            player.health=val(p,'health',500,0,player.max_health)
            if player.health<=0:
                raise ValueError('Finished checkpoint')
            player.armor=val(p,'armor',0,0,75)
            player.stamina=val(p,'stamina',100,0,100)
            player.selected=int(val(p,'selected',1,0,3))
            for key,high in (('damage',3),('fire_rate',2.2),('speed_bonus',1.6),('reload_speed',2.6)):
                setattr(player,key,val(p,key,1,1,high))
            for w,raw in zip(player.weapons,p.get('weapons',[])[:4]):
                if not isinstance(raw,dict):
                    raise ValueError('Invalid weapon')
                w.ammo=int(val(raw,'ammo',w.spec.magazine,0,w.spec.magazine))
                w.reserve=int(val(raw,'reserve',w.spec.reserve,0,w.spec.reserve*2))
                w.reload_duration=val(raw,'reload_duration',w.spec.reload,.1,4)
                w.reload_left=val(raw,'reload_left',0,0,w.reload_duration)
                w.cooldown=val(raw,'cooldown',0,0,2)
            manager=WaveManager(wave['mode'])
            manager.number=int(val(wave,'number',1,1,10000))
            manager.phase=wave.get('phase')
            if manager.phase not in ('intro','combat','intermission'):
                raise ValueError('Invalid wave')
            manager.pending=[k for k in wave.get('pending',[])[:50] if k in ENEMIES]
            manager.timer=val(wave,'timer',0,0,3)
            manager.spawn_timer=val(wave,'spawn_timer',0,0,2)
            manager.choices=[k for k in wave.get('choices',[])[:3] if k in UPGRADES]
            if manager.phase=='intermission' and len(manager.choices)!=3:
                manager.choices=self.rng.sample(list(UPGRADES),3)
            enemies=[]
            for raw in snap.get('enemies',[])[:30]:
                kind=raw.get('kind')
                if kind not in ENEMIES:
                    raise ValueError('Invalid enemy')
                enemy=Enemy(kind,vec(raw['pos']),manager.number,self.rng)
                enemy.pos=self.world.resolve(enemy.pos,enemy.radius)
                enemy.max_health=val(raw,'max_health',enemy.max_health,1,50000)
                enemy.health=val(raw,'health',enemy.max_health,0,enemy.max_health)
                enemy.cooldown=val(raw,'cooldown',1,0,5)
                enemy.age=val(raw,'age',1,0,100000)
                enemy.has_retreated=raw.get('has_retreated') is True
                if enemy.health>0:
                    enemies.append(enemy)
            bullets=[]
            for raw in snap.get('bullets',[])[:500]:
                velocity=raw['velocity']
                if not isinstance(velocity,list) or len(velocity)!=2 or raw.get('owner') not in ('player','enemy'):
                    raise ValueError('Invalid projectile')
                vel=pygame.Vector2(number(velocity[0],0,-2500,2500),number(velocity[1],0,-2500,2500))
                bullets.append(Bullet(vec(raw['pos']),vel,raw['owner'],val(raw,'damage',20,1,1200),
                                      val(raw,'life',1,0,3),raw.get('critical') is True,int(val(raw,'shot_id',0,0,10**9))))
            stats=self.empty_stats()
            source=snap.get('stats',{})
            for key in stats:
                stats[key]=val(source,key,0,0,10**10)
                if key!='time':
                    stats[key]=int(stats[key])
            stats['hits']=min(stats['hits'],stats['shots'])
            pickups=[]
            for raw in snap.get('pickups',[])[:50]:
                if raw.get('kind') in ('medkit','ammo'):
                    pickups.append({'pos':vec(raw['pos']),'kind':raw['kind'],'life':val(raw,'life',1,0,18)})
            difficulty=snap.get('difficulty') if snap.get('difficulty') in DIFFICULTIES else 'Regular'
            counter=int(val(snap,'shot_counter',stats['shots'],0,10**9))
            ids={int(i) for i in snap.get('hit_ids',[])[:1000] if isinstance(i,int) and 0<=i<=counter}
            combo=int(val(snap,'combo',0,0,10000))
            combo_left=val(snap,'combo_left',0,0,3)
            # Commit only after the entire checkpoint validates successfully.
            self.player,self.wave,self.enemies,self.bullets=player,manager,enemies,bullets
            self.pickups,self.stats=pickups,stats
            self.corpses,self.floating,self.notifications=[],[],[]
            self.particles.items.clear()
            self.run_difficulty=difficulty
            self.difficulty_factor=DIFFICULTIES[self.run_difficulty]
            self.shot_counter=counter
            self.hit_ids=ids
            self.combo=combo
            self.combo_left=combo_left
            self.has_run=True
            self.run_finished=False
            self.ui.health_display=player.health
            self.ui.score_display=stats['score']
            self.change_state('upgrade' if manager.phase=='intermission' else 'playing')
            self.audio.pause(self.state!='playing')
            self.camera.follow(player.pos,player.pos,0,instant=True)
            self.announce('BACK IN THE FIELD',f'WAVE {manager.number:02d} / {self.run_difficulty.upper()}')
            return True
        except (KeyError,TypeError,ValueError,AttributeError,OverflowError):
            self.save.data['checkpoint']=None
            self.save.write()
            self.save.warning='Checkpoint unreadable. Start a fresh mission.'
            return False

    def change_setting(self,key,direction):
        s=self.settings
        if key in ('fullscreen','shake'):
            s[key]=not s[key]
        elif key=='resolution':
            index=RESOLUTIONS.index(tuple(s[key]))
            s[key]=list(RESOLUTIONS[(index+direction)%len(RESOLUTIONS)])
        elif key=='quality':
            s[key]='Low' if s[key]=='High' else 'High'
        elif key=='difficulty':
            values=list(DIFFICULTIES)
            s[key]=values[(values.index(s[key])+direction)%len(values)]
        elif key in ('master','music','sfx'):
            s[key]=round(max(0,min(1,s[key]+direction*.1)),2)
        elif key=='sensitivity':
            s[key]=round(max(.4,min(2,s[key]+direction*.1)),1)
        if key in ('fullscreen','resolution'):
            self.set_display()
        self.audio.apply(s)
        self.save.write()

    def action(self,action):
        if action is None:
            return
        self.audio.play('menu',.6)
        if isinstance(action,tuple):
            if action[0]=='start':
                self.start(action[1])
            elif action[0]=='setting':
                self.change_setting(action[1],action[2])
            elif action[0]=='upgrade':
                self.wave.apply_upgrade(self,action[1])
                pygame.mouse.set_visible(False)
            return
        if action=='deploy':
            self.parent='menu'
            self.change_state('deploy')
        elif action=='continue':
            self.restore()
        elif action in ('settings','controls','credits'):
            self.parent=self.state
            self.change_state(action)
        elif action=='back':
            self.change_state(self.parent)
        elif action=='resume':
            self.change_state('playing')
            self.audio.pause(False)
        elif action=='restart':
            self.start(self.wave.mode)
        elif action=='main_menu':
            if self.state not in ('game_over','victory'):
                self.save_checkpoint()
            self.change_state('menu')
            self.audio.pause(False)
        elif action=='defaults':
            self.settings.clear()
            self.settings.update(copy.deepcopy(DEFAULT_SETTINGS))
            self.set_display()
            self.audio.apply(self.settings)
            self.save.write()
        elif action=='quit':
            self.close()

    def handle_events(self,events):
        for event in events:
            if event.type==pygame.QUIT:
                self.close()
            elif event.type==pygame.WINDOWFOCUSLOST and self.state=='playing':
                self.pause()
            elif event.type==pygame.VIDEORESIZE and not self.settings['fullscreen']:
                self.resize_viewport(self.display.get_size())
            elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and self.state!='playing':
                point=self.logical_mouse(event.pos)
                if self.viewport.collidepoint(event.pos):
                    self.action(self.ui.click(point))
            elif event.type==pygame.MOUSEWHEEL and self.state=='playing':
                self.player.switch(self.player.selected-event.y)
            elif event.type==pygame.KEYDOWN:
                key=event.key
                if key==pygame.K_F11:
                    self.change_setting('fullscreen',1)
                elif key==pygame.K_ESCAPE:
                    if self.state in ('playing','pause'):
                        self.pause()
                    elif self.state in ('settings','controls','credits','deploy'):
                        self.action('back')
                elif key==pygame.K_p and self.state in ('playing','pause'):
                    self.pause()
                elif self.state=='playing':
                    if key==pygame.K_r and self.player.weapon.reload(self.player.reload_speed):
                        self.audio.play('reload')
                    elif key==pygame.K_SPACE and self.player.dodge(self.input.movement):
                        self.audio.play('dodge')
                    elif key in (pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4):
                        self.player.switch(key-pygame.K_1)
                elif self.state=='game_over' and key==pygame.K_r:
                    self.action('restart')
                elif self.state=='upgrade' and key in (pygame.K_1,pygame.K_2,pygame.K_3):
                    index=key-pygame.K_1
                    if index<len(self.wave.choices):
                        self.action(('upgrade',self.wave.choices[index]))
                elif self.state=='menu' and key==pygame.K_RETURN:
                    self.action('deploy')

    def poll_input(self):
        keys=pygame.key.get_pressed()
        movement=pygame.Vector2(int(keys[pygame.K_d] or keys[pygame.K_RIGHT])-int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
                                int(keys[pygame.K_s] or keys[pygame.K_DOWN])-int(keys[pygame.K_w] or keys[pygame.K_UP]))
        self.mouse=self.logical_mouse(pygame.mouse.get_pos())
        aim=self.camera.unproject(self.mouse,17)
        fire=pygame.mouse.get_pressed()[0] and self.viewport.collidepoint(pygame.mouse.get_pos())
        self.input=InputFrame(movement,aim,fire,keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        return self.input

    def draw(self,mouse=None,present=True):
        if mouse is not None:
            self.mouse=pygame.Vector2(mouse)
        surf=self.canvas
        self.renderer.scene(surf,self,menu=not self.has_run)
        self.ui.begin(self.mouse,self.last_dt)
        if self.has_run and self.state!='menu' and self.state!='deploy':
            self.ui.hud(surf,self)
        if self.state=='playing':
            self.ui.crosshair(surf,self)
        elif self.state=='menu':
            self.ui.menu(surf,self)
        elif self.state=='deploy':
            self.ui.deploy(surf,self)
        elif self.state=='pause':
            self.ui.pause(surf,self)
        elif self.state=='controls':
            self.ui.controls(surf)
        elif self.state=='settings':
            self.ui.settings(surf,self)
        elif self.state=='credits':
            self.ui.credits(surf)
        elif self.state=='upgrade':
            self.ui.upgrade(surf,self)
        elif self.state in ('game_over','victory'):
            self.ui.end_screen(surf,self,self.state=='victory')
        if self.transition>0:
            self.ui.overlay.fill((5,12,19,int(self.transition*160)))
            surf.blit(self.ui.overlay,(0,0))
        if present:
            self.display.fill((5,10,14))
            if self.viewport.size==(WIDTH,HEIGHT):
                self.display.blit(surf,self.viewport)
            else:
                self.display.blit(pygame.transform.smoothscale(surf,self.viewport.size),self.viewport)
            pygame.display.flip()
        return surf

    def close(self):
        if self.has_run and self.state not in ('game_over','victory'):
            self.save_checkpoint()
        else:
            self.save.write()
        self.running=False
