from dataclasses import dataclass
import math
import pygame
from config import WIDTH,HEIGHT,ACCENT,AMBER,RED,TEXT,MUTED,PANEL,WORLD_W,WORLD_H,RESOLUTIONS,DIFFICULTIES
from systems.wave_manager import UPGRADES


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: object
    disabled: bool=False


class Interface:
    def __init__(self,assets):
        self.assets=assets
        self.buttons=[]
        self.hover={}
        self.panel_cache={}
        self.mouse=pygame.Vector2()
        self.dt=1/60
        self.health_display=500.0
        self.score_display=0.0
        self.overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        self.damage_direction=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)

    def text(self,surf,value,pos,size=18,color=TEXT,kind='interface',align='left'):
        img=self.assets.text(value,size,color,kind)
        rect=img.get_rect()
        if align=='center':
            rect.center=pos
        elif align=='right':
            rect.topright=pos
        else:
            rect.topleft=pos
        surf.blit(img,rect)
        return rect

    def begin(self,mouse,dt):
        self.buttons=[]
        self.mouse=pygame.Vector2(mouse)
        self.dt=dt

    def panel(self,surf,rect,alpha=230,border=True):
        rect=pygame.Rect(rect)
        key=(rect.w,rect.h,alpha,border)
        if key not in self.panel_cache:
            panel=pygame.Surface(rect.size,pygame.SRCALPHA)
            local=panel.get_rect()
            pygame.draw.rect(panel,(*PANEL,alpha),local,border_radius=6)
            if border:
                pygame.draw.rect(panel,(87,112,111,125),local,1,border_radius=6)
                pygame.draw.line(panel,(*ACCENT,210),(0,0),(22,0),2)
            self.panel_cache[key]=panel
        surf.blit(self.panel_cache[key],rect)

    def button(self,surf,rect,label,action,disabled=False,primary=False,index=None):
        rect=pygame.Rect(rect)
        self.buttons.append(Button(rect,label,action,disabled))
        key=str(action)
        hover=rect.collidepoint(self.mouse) and not disabled
        value=self.hover.get(key,0)+(int(hover)-self.hover.get(key,0))*min(1,self.dt*12)
        self.hover[key]=value
        color=ACCENT if primary else TEXT
        fill=(int(25+value*15),int(41+value*20),int(47+value*18))
        if primary:
            fill=tuple(int(c*(.7+value*.18)) for c in ACCENT)
            color=(13,31,34)
        if disabled:
            fill,color=(23,32,37),(78,91,96)
        polygon=[rect.topleft,(rect.right-9,rect.top), (rect.right,rect.top+9),
                 rect.bottomright,(rect.left+9,rect.bottom),(rect.left,rect.bottom-9)]
        pygame.draw.polygon(surf,fill,polygon)
        pygame.draw.polygon(surf,tuple(int(c*(.5+value*.4)) for c in (ACCENT if hover or primary else MUTED)),polygon,1)
        if index is not None:
            self.text(surf,index,(rect.x+16,rect.centery),13,color,'mono','center')
        if rect.w<60:
            self.text(surf,label,rect.center,16,color,'heading','center')
        else:
            self.text(surf,label,(rect.x+(44 if index is not None else 20),rect.y+(rect.h-22)//2),16,color,'heading')
        if not disabled and rect.w>=60:
            x=rect.right-27+value*4
            pygame.draw.lines(surf,color,False,[(x-4,rect.centery-4),(x,rect.centery),(x-4,rect.centery+4)],2)

    def click(self,point):
        for button in reversed(self.buttons):
            if not button.disabled and button.rect.collidepoint(point):
                return button.action
        return None

    def logo(self,surf,pos,scale=1):
        x,y=pos
        for i in range(3):
            pygame.draw.polygon(surf,ACCENT,[(x+i*10*scale,y+24*scale),(x+i*10*scale+6*scale,y+24*scale),
                                          (x+i*10*scale+19*scale,y),(x+i*10*scale+13*scale,y)])

    def menu(self,surf,game):
        surf.blit(self.assets.menu_shade,(0,0))
        self.logo(surf,(76,47))
        self.text(surf,'TACTICAL SURVIVAL / V2.0',(127,48),13,ACCENT,'mono')
        self.text(surf,'AI',(72,106),91,TEXT,'heading')
        self.text(surf,'MILITIA',(72,190),91,TEXT,'heading')
        pygame.draw.line(surf,ACCENT,(80,308),(119,308),3)
        self.text(surf,'COMBAT ZONE',(133,290),24,MUTED,'heading')
        labels=[('DEPLOY', 'deploy'),('CONTINUE','continue'),('SETTINGS','settings'),
                ('CONTROLS','controls'),('CREDITS','credits'),('QUIT','quit')]
        for i,(label,action) in enumerate(labels):
            self.button(surf,(80,355+i*56,300,46),label,action,
                        disabled=action=='continue' and not game.save.data['checkpoint'],primary=i==0,index=f'{i+1:02}')
        self.text(surf,'YOUR BEST',(80,725),11,MUTED,'mono')
        self.text(surf,f"{game.save.data['high_score']:,}",(185,719),23,AMBER,'heading')
        self.text(surf,'AIM. ADAPT. SURVIVE.',(80,764),11,MUTED,'mono')
        self.text(surf,'SECTOR 07  /  FORWARD OPERATING BASE',(1324,48),12,MUTED,'mono','right')
        # A large procedural operative and calibration rings anchor the right half.
        center=(1040,380)
        for radius in (145,180,228):
            pygame.draw.circle(surf,(58,82,82),center,radius,1)
        pygame.draw.arc(surf,ACCENT,(860,200,360,360),game.visual_time*.12,game.visual_time*.12+.5,2)
        for x,y in ((790,370),(1290,370),(1040,130),(1040,630)):
            pygame.draw.line(surf,(87,117,113),(x-6,y),(x+6,y),1)
            pygame.draw.line(surf,(87,117,113),(x,y-6),(x,y+6),1)
        hero=self.assets.actor('player',-36,'rifle',3.9)
        surf.blit(hero,hero.get_rect(center=(1040,390+math.sin(game.visual_time)*4)))
        self.text(surf,'OPERATIVE // 07',(796,623),13,ACCENT,'mono')
        self.text(surf,'NO BACKUP. NO SECOND CHANCES.',(796,650),18,TEXT,'heading')
        self.text(surf,'Four weapons. Adaptive hostiles. One extraction.',(796,681),14,MUTED)
        pygame.draw.line(surf,(73,98,99),(797,717),(1318,717),1)
        self.text(surf,'500 HP  /  4 WEAPONS  /  6 ENEMY CLASSES',(796,734),11,MUTED,'mono')
        if game.save.warning:
            self.text(surf,game.save.warning,(700,774),12,AMBER,'interface','center')

    def frame(self,surf,title,subtitle):
        self.overlay.fill((6,14,21,180))
        surf.blit(self.overlay,(0,0))
        self.panel(surf,(250,100,900,600),245)
        self.logo(surf,(287,132),.8)
        self.text(surf,title,(338,125),31,TEXT,'heading')
        self.text(surf,subtitle,(289,185),14,MUTED)
        pygame.draw.line(surf,(56,78,80),(290,220),(1110,220),1)

    def deploy(self,surf,game):
        self.frame(surf,'SELECT OPERATION','Choose your mission. Difficulty is set in Settings.')
        cards=[(290,'operation','OPERATION: IRON VEIL','10 waves / bosses at 05 and 10','Secure the depot and defeat the final commander.'),
               (710,'survival','ENDLESS SURVIVAL','Unlimited waves / escalating pressure','The original survival concept, with a new arsenal.')]
        for x,key,title,info,desc in cards:
            self.panel(surf,(x,254,400,320),235)
            self.text(surf,'01' if key=='operation' else '02',(x+24,274),55,ACCENT if key=='operation' else AMBER,'mono')
            self.text(surf,title,(x+24,357),19,TEXT,'heading')
            self.text(surf,info,(x+24,397),13,ACCENT,'mono')
            # Wrap the descriptive copy into two short lines deliberately.
            lines= ['Secure the depot and defeat','the final commander.'] if key=='operation' else ['The original survival concept,','with a new arsenal.']
            for i,line in enumerate(lines):
                self.text(surf,line,(x+24,435+i*23),15,MUTED)
            self.button(surf,(x+24,505,351,44),'START MISSION',('start',key),primary=key=='operation')
        self.text(surf,f"RULES OF ENGAGEMENT / {game.settings['difficulty'].upper()}",(292,616),12,AMBER,'mono')
        self.button(surf,(885,619,225,43),'BACK','back')

    def controls(self,surf):
        self.frame(surf,'FIELD MANUAL','Movement is on the ground plane. Mouse aims above the character at weapon height.')
        rows=[('W A S D / ARROWS','Move'),('MOUSE / LEFT CLICK','Aim / hold to fire'),
              ('R','Reload / retry after defeat'),('LEFT / RIGHT SHIFT','Sprint while stamina lasts'),
              ('SPACE','Dodge in movement or aim direction'),('1 2 3 4 / MOUSE WHEEL','Pistol / rifle / shotgun / sniper'),
              ('ESC / P','Pause / resume'),('F11','Toggle fullscreen')]
        for i,(key,label) in enumerate(rows):
            y=250+i*43
            self.text(surf,key,(292,y),15,ACCENT,'mono')
            self.text(surf,label,(664,y),16,TEXT)
            pygame.draw.line(surf,(38,56,59),(292,y+31),(1105,y+31),1)
        self.text(surf,'TIP: Cover stops bullets. Dodge through danger. Refill and upgrade after every wave.',(292,607),13,AMBER)
        self.button(surf,(885,643,225,38),'BACK','back')

    def credits(self,surf):
        self.frame(surf,'MISSION DOSSIER','AI Militia: Combat Zone / upgraded Pygame edition')
        lines=[('ORIGINAL FOUNDATION','militia.py — top-down player combat, three bots, cover and scoring.'),
               ('VISUAL DIRECTION','Procedural military arena, tilted projection, shadows and animated effects.'),
               ('ENGINE & AUDIO','Python + pygame-ce. Synthesized sound effects and ambient music.'),
               ('FONT LICENSE','DejaVu Sans. The included font license is in assets/fonts/LICENSE.txt.'),
               ('CUSTOMIZATION','Drop optional graphics and audio into assets; see the README.')]
        for i,(heading,body) in enumerate(lines):
            y=262+i*68
            self.text(surf,heading,(292,y),12,ACCENT,'mono')
            self.text(surf,body,(292,y+23),16,TEXT)
        self.button(surf,(885,628,225,42),'BACK','back')

    def settings(self,surf,game):
        self.frame(surf,'SYSTEM SETTINGS','Changes save automatically. Mission difficulty takes effect when starting a new run.')
        s=game.settings
        self.text(surf,'DISPLAY & EFFECTS',(293,240),12,ACCENT,'mono')
        self.text(surf,'AUDIO & GAMEPLAY',(720,240),12,ACCENT,'mono')
        left=[('resolution','RESOLUTION',f"{s['resolution'][0]} x {s['resolution'][1]}"),
              ('fullscreen','SCREEN MODE','FULLSCREEN' if s['fullscreen'] else 'WINDOWED'),
              ('quality','EFFECTS QUALITY',s['quality'].upper()),('shake','CAMERA SHAKE','ON' if s['shake'] else 'OFF')]
        right=[('master','MASTER VOLUME',f"{round(s['master']*100)}%"),('music','MUSIC VOLUME',f"{round(s['music']*100)}%"),
               ('sfx','SFX VOLUME',f"{round(s['sfx']*100)}%"),('sensitivity','AIM RESPONSE',f"{s['sensitivity']:.1f}x"),
               ('difficulty','DIFFICULTY',s['difficulty'].upper())]
        for x,rows in ((292,left),(720,right)):
            for i,(key,label,value) in enumerate(rows):
                y=272+i*64
                self.text(surf,label,(x,y),11,MUTED,'mono')
                self.button(surf,(x,y+21,45,30),'-',('setting',key,-1))
                self.text(surf,value,(x+172,y+35),14,TEXT,'heading','center')
                self.button(surf,(x+300,y+21,45,30),'+',('setting',key,1))
        self.text(surf,'AIM RESPONSE changes rotation smoothing, so the crosshair stays under your mouse.',(292,618),12,MUTED)
        self.button(surf,(292,644,225,38),'RESET DEFAULTS','defaults')
        self.button(surf,(885,644,225,38),'DONE','back',primary=True)

    def pause(self,surf,game):
        self.overlay.fill((6,14,21,166))
        surf.blit(self.overlay,(0,0))
        self.panel(surf,(494,130,412,545),246)
        self.text(surf,'MISSION PAUSED',(700,187),31,TEXT,'heading','center')
        self.text(surf,'TAKE A BREATH. HOLD THE LINE.',(700,236),11,ACCENT,'mono','center')
        for i,(label,key) in enumerate([('RESUME','resume'),('RESTART','restart'),('SETTINGS','settings'),
                                       ('MAIN MENU','main_menu'),('QUIT','quit')]):
            self.button(surf,(532,280+i*67,336,48),label,key,primary=i==0,index=f'{i+1:02}')
        self.text(surf,'ESC TO RESUME',(700,646),11,MUTED,'mono','center')

    def upgrade(self,surf,game):
        self.overlay.fill((6,14,21,195))
        surf.blit(self.overlay,(0,0))
        self.text(surf,'SECTOR SECURED',(700,161),44,TEXT,'heading','center')
        self.text(surf,f'WAVE {game.wave.number:02d} COMPLETE / SELECT ONE FIELD UPGRADE',(700,216),13,ACCENT,'mono','center')
        self.text(surf,'All weapons resupplied. +45 health. +25 armor. Combat is paused.',(700,248),16,MUTED,'interface','center')
        for i,key in enumerate(game.wave.choices):
            x=160+i*370
            title,description,icon=UPGRADES[key]
            rect=pygame.Rect(x,308,340,260)
            self.panel(surf,rect,245)
            self.text(surf,icon,(x+25,333),45,ACCENT,'mono')
            self.text(surf,title,(x+25,411),20,TEXT,'heading')
            self.text(surf,description,(x+25,450),14,MUTED)
            self.button(surf,(x+24,502,292,43),f'SELECT [{i+1}]',('upgrade',key),primary=True)
        self.button(surf,(535,624,330,45),'CONTINUE WITHOUT UPGRADE',('upgrade',None))

    def end_screen(self,surf,game,victory=False):
        self.overlay.fill((6,14,21,205))
        surf.blit(self.overlay,(0,0))
        self.panel(surf,(370,111,660,584),247)
        self.text(surf,'MISSION COMPLETE' if victory else 'OPERATIVE DOWN',(700,173),39,ACCENT if victory else RED,'heading','center')
        self.text(surf,'EXTRACTION CONFIRMED' if victory else 'THE FIGHT IS NOT OVER.',(700,225),12,MUTED,'mono','center')
        stats=game.stats
        accuracy=100*stats['hits']/max(1,stats['shots'])
        minutes,seconds=divmod(int(stats['time']),60)
        rows=[('FINAL SCORE',f"{stats['score']:,}"),('HOSTILES ELIMINATED',str(stats['kills'])),
              ('ACCURACY',f'{accuracy:.1f}%'),('WAVE REACHED',f'{game.wave.number:02}'),
              ('TIME IN THE FIELD',f'{minutes:02}:{seconds:02}'),('PRECISION KILLS',str(stats['precision']))]
        for i,(label,value) in enumerate(rows):
            y=280+i*44
            self.text(surf,label,(417,y),13,MUTED,'mono')
            self.text(surf,value,(976,y-3),21,TEXT,'heading','right')
            pygame.draw.line(surf,(42,59,63),(417,y+33),(979,y+33),1)
        self.button(surf,(415,579,174,46),'RETRY','restart',primary=True)
        self.button(surf,(608,579,195,46),'MAIN MENU','main_menu')
        self.button(surf,(822,579,163,46),'QUIT','quit')
        self.text(surf,f"PERSONAL BEST / {game.save.data['high_score']:,}",(700,659),12,AMBER,'mono','center')

    def hud(self,surf,game):
        p,w=game.player,game.player.weapon
        self.health_display+=(p.health-self.health_display)*min(1,self.dt*10)
        self.score_display+=(game.stats['score']-self.score_display)*min(1,self.dt*12)
        self.panel(surf,(28,25,309,94),205)
        self.text(surf,'OPERATIVE 07',(47,39),11,ACCENT,'mono')
        self.text(surf,f'{int(p.health):03} / {int(p.max_health)}',(318,35),18,TEXT,'heading','right')
        pygame.draw.rect(surf,(43,57,59),(47,69,271,9),border_radius=3)
        ratio=max(0,min(1,self.health_display/p.max_health))
        color=ACCENT if ratio>.3 else RED
        pygame.draw.rect(surf,color,(47,69,max(1,int(271*ratio)),9),border_radius=3)
        for i in range(10):
            x=47+i*28
            pygame.draw.rect(surf,(70,120,145) if p.armor/p.max_armor>(i/10) else (40,52,58),(x,85,21,4),border_radius=1)
        self.text(surf,f'ARMOR {int(p.armor):02}',(47,97),10,MUTED,'mono')
        self.text(surf,'SHIFT / SPRINT',(318,97),10,MUTED,'mono','right')
        self.panel(surf,(1080,25,292,93),205)
        self.text(surf,'SCORE',(1100,39),11,MUTED,'mono')
        self.text(surf,f"{int(self.score_display):,}",(1351,33),27,TEXT,'heading','right')
        self.text(surf,f"KILLS  {game.stats['kills']:03}",(1100,86),11,ACCENT,'mono')
        self.text(surf,f"WAVE  {game.wave.number:02}",(1351,86),11,AMBER,'mono','right')
        self.panel(surf,(520,25,360,43),210)
        count=len(game.enemies)+len(game.wave.pending)
        label=f'WAVE {game.wave.number:02} / {count:02} HOSTILES' if game.wave.phase=='combat' else f'DEPLOYING / {game.wave.timer:.1f}s'
        self.text(surf,label,(700,47),13,TEXT,'mono','center')
        self.panel(surf,(28,655,395,118),215)
        self.assets.gun_icon(surf,(50,690),w.spec.key,ACCENT,1.1)
        self.text(surf,w.spec.title,(126,672),14,TEXT,'heading')
        self.text(surf,f'{w.ammo:02}',(50,712),37,AMBER if w.ammo<=max(2,w.spec.magazine*.2) else TEXT,'heading')
        self.text(surf,f"/ {'INF' if w.spec.key=='pistol' else w.reserve:}",(117,732),18,MUTED,'mono')
        if w.reloading:
            t=1-w.reload_left/max(.1,w.reload_duration)
            self.text(surf,'RELOADING',(386,719),12,ACCENT,'mono','right')
            pygame.draw.rect(surf,(45,62,64),(213,742,173,4))
            pygame.draw.rect(surf,ACCENT,(213,742,173*t,4))
        else:
            self.text(surf,'R / RELOAD',(386,733),11,MUTED,'mono','right')
        self.panel(surf,(454,706,492,67),195)
        for i,weapon in enumerate(p.weapons):
            x=467+i*122
            color=ACCENT if i==p.selected else (102,120,120)
            if i==p.selected:
                pygame.draw.line(surf,color,(x,715),(x+103,715),2)
            self.text(surf,str(i+1),(x,729),11,color,'mono')
            self.assets.gun_icon(surf,(x+23,736),weapon.spec.key,color,.78)
            self.text(surf,weapon.spec.key.upper(),(x+14,755),9,color,'mono')
        self.panel(surf,(1098,568,274,205),200)
        self.text(surf,'TACTICAL OVERVIEW',(1117,582),10,MUTED,'mono')
        minimap=pygame.Rect(1117,607,236,141)
        pygame.draw.rect(surf,(25,38,42),minimap,border_radius=3)
        for o in game.world.obstacles:
            r=o.rect
            pygame.draw.rect(surf,(77,93,89),(minimap.x+r.x/WORLD_W*minimap.w,minimap.y+r.y/WORLD_H*minimap.h,
                                             max(2,r.w/WORLD_W*minimap.w),max(2,r.h/WORLD_H*minimap.h)))
        for enemy in game.enemies:
            q=(int(minimap.x+enemy.pos.x/WORLD_W*minimap.w),int(minimap.y+enemy.pos.y/WORLD_H*minimap.h))
            pygame.draw.circle(surf,RED,q,3 if enemy.kind!='boss' else 5)
        q=(minimap.x+p.pos.x/WORLD_W*minimap.w,minimap.y+p.pos.y/WORLD_H*minimap.h)
        pygame.draw.circle(surf,ACCENT,q,4)
        self.text(surf,'N',(1350,754),10,ACCENT,'mono','right')
        self.text(surf,'ESC / PAUSE',(1117,754),10,MUTED,'mono')
        pygame.draw.rect(surf,(44,57,56),(520,685,360,4),border_radius=2)
        pygame.draw.rect(surf,ACCENT,(520,685,360*p.stamina/100,4),border_radius=2)
        bosses=[e for e in game.enemies if e.kind=='boss']
        if bosses:
            boss=bosses[0]
            self.panel(surf,(475,84,450,63),225)
            self.text(surf,'COMMANDER / HEAVY CONTACT',(700,103),12,AMBER,'mono','center')
            pygame.draw.rect(surf,(75,44,40),(494,125,412,7),border_radius=2)
            pygame.draw.rect(surf,RED,(494,125,max(1,412*boss.health/boss.max_health),7),border_radius=2)
        if game.announcement_left>0:
            self.text(surf,game.announcement,(700,207),40,TEXT,'heading','center')
            self.text(surf,game.announcement_sub,(700,250),13,AMBER,'mono','center')
        for i,n in enumerate(game.notifications[-4:]):
            color=ACCENT if n['color']=='accent' else AMBER
            self.text(surf,n['text'],(50,150+i*27),13,color,'mono')
        if game.combo>=2 and game.combo_left>0:
            self.text(surf,f'{game.combo}x CHAIN',(700,622),18,AMBER,'heading','center')
        if p.hit_flash>0:
            angle=math.radians(p.last_damage_angle)
            direction=pygame.Vector2(math.cos(angle),math.sin(angle)*.8).normalize()
            center=pygame.Vector2(WIDTH/2,HEIGHT/2)+direction*170
            side=pygame.Vector2(-direction.y,direction.x)
            pygame.draw.polygon(surf,RED,[center+direction*13,center-direction*8+side*10,center-direction*8-side*10])

    def crosshair(self,surf,game):
        pos=self.mouse
        gap=7+game.player.recoil*.65+min(8,game.player.velocity.length()*.015)
        color=AMBER if game.hit_marker>0 and game.critical_marker else TEXT
        if game.hit_marker>0 and not game.critical_marker:
            color=ACCENT
        x,y=pos
        pygame.draw.circle(surf,(7,16,19),(int(x),int(y)),2)
        pygame.draw.circle(surf,color,(int(x),int(y)),1)
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            a=(x+dx*gap,y+dy*gap)
            b=(x+dx*(gap+7),y+dy*(gap+7))
            pygame.draw.line(surf,(9,21,23),a,b,4)
            pygame.draw.line(surf,color,a,b,2)
        if game.hit_marker>0:
            for dx,dy in ((1,1),(-1,1),(1,-1),(-1,-1)):
                pygame.draw.line(surf,color,(x+dx*4,y+dy*4),(x+dx*8,y+dy*8),2)
        if game.player.weapon.reloading:
            progress=1-game.player.weapon.reload_left/game.player.weapon.reload_duration
            pygame.draw.arc(surf,ACCENT,(x-20,y-20,40,40),-math.pi/2,-math.pi/2+max(.02,progress*math.tau),2)
