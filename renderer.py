import math
import pygame
from config import WIDTH,HEIGHT,TILT,ACCENT,AMBER,RED,TEXT,MUTED


class Renderer:
    def __init__(self,assets):
        self.assets=assets
        self.shadow=pygame.Surface((90,42),pygame.SRCALPHA)
        pygame.draw.ellipse(self.shadow,(3,9,13,90),(1,1,88,40))
        self.afterimage=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)

    def obstacle(self,surf,camera,obj):
        r=obj.rect
        top=camera.project((r.x,r.y),obj.height)
        bottom=camera.project((r.right,r.bottom))
        if bottom.x<-80 or top.x>WIDTH+80 or bottom.y<-80 or top.y>HEIGHT+80:
            return
        w,h=r.w,r.h*TILT
        roof=pygame.Rect(int(top.x),int(top.y),w,int(h))
        palettes={
            'barrier':((133,132,104),(75,78,66),(52,62,56)),
            'building':((91,115,118),(51,70,73),(37,55,58)),
            'container':((89,117,109),(49,73,68),(32,52,51)),
            'crate':((131,113,75),(82,75,53),(58,57,42)),
            'vehicle':((87,99,85),(48,64,57),(32,48,44)),
        }
        color,front,side=palettes[obj.kind]
        pygame.draw.polygon(surf,front,[(roof.left,roof.bottom),(roof.right,roof.bottom),
                                      (roof.right,roof.bottom+obj.height),(roof.left,roof.bottom+obj.height)])
        pygame.draw.polygon(surf,side,[(roof.right,roof.top),(roof.right+6,roof.top+6),
                                     (roof.right+6,roof.bottom+obj.height),(roof.right,roof.bottom+obj.height)])
        pygame.draw.rect(surf,color,roof,border_radius=2)
        pygame.draw.line(surf,tuple(min(255,c+25) for c in color),roof.topleft,roof.topright,2)
        pygame.draw.line(surf,(30,42,42),roof.bottomleft,roof.bottomright,2)
        if obj.kind=='barrier':
            for x in range(roof.left+8,roof.right-6,37):
                pygame.draw.line(surf,(61,67,56),(x,roof.top+5),(x,roof.bottom-5),1)
                pygame.draw.line(surf,AMBER,(x,roof.bottom+6),(x+12,roof.bottom+18),4)
        elif obj.kind in ('building','container'):
            for y in range(roof.top+9,roof.bottom-4,13):
                pygame.draw.line(surf,tuple(max(0,c-11) for c in color),(roof.left+6,y),(roof.right-6,y),2)
            if obj.kind=='building':
                vent=pygame.Rect(roof.x+roof.w*.62,roof.y+roof.h*.35,50,29)
                pygame.draw.rect(surf,(41,61,66),vent,border_radius=2)
                for y in range(vent.y+5,vent.bottom-3,5):
                    pygame.draw.line(surf,(113,132,130),(vent.x+4,y),(vent.right-4,y),1)
                for x in range(roof.left+20,roof.right-25,72):
                    pygame.draw.rect(surf,(14,33,39),(x,roof.bottom+17,36,20),border_radius=2)
                    pygame.draw.line(surf,(171,166,116),(x+2,roof.bottom+20),(x+33,roof.bottom+20),2)
            label=self.assets.text(obj.label,13,(169,184,171),'mono')
            surf.blit(label,(roof.x+12,roof.y+11))
        elif obj.kind=='crate':
            inner=roof.inflate(-12,-12)
            pygame.draw.rect(surf,(81,76,53),inner,2)
            pygame.draw.line(surf,(175,155,109),inner.topleft,inner.bottomright,3)
            pygame.draw.line(surf,(175,155,109),inner.topright,inner.bottomleft,3)
            for x in (roof.x+4,roof.right-5):
                pygame.draw.circle(surf,(211,186,128),(x,roof.y+5),2)
        elif obj.kind=='vehicle':
            inner=roof.inflate(-16,-12)
            pygame.draw.rect(surf,(46,69,74),inner,border_radius=5)
            if roof.w>roof.h:
                pygame.draw.rect(surf,(18,39,44),(roof.centerx-14,roof.y+5,28,roof.h-10),border_radius=2)
            else:
                pygame.draw.rect(surf,(18,39,44),(roof.x+5,roof.y+roof.h*.34,roof.w-10,22),border_radius=2)
            pygame.draw.line(surf,(175,176,138),(roof.right-3,roof.top+10),(roof.right-3,roof.top+24),3)

    def actor(self,surf,camera,actor,kind,weapon,quality):
        ground=camera.project(actor.pos)
        if not (-100<ground.x<WIDTH+100 and -100<ground.y<HEIGHT+100):
            return
        scale=1.7 if kind=='boss' else 1.2 if kind=='heavy' else 1
        shadow=self.shadow if scale==1 else pygame.transform.scale(self.shadow,(int(90*scale),int(42*scale)))
        surf.blit(shadow,shadow.get_rect(center=(ground.x+10,ground.y+8)))
        if kind=='player':
            pygame.draw.ellipse(surf,(83,181,167),(ground.x-24,ground.y-12,48,24),1)
            if actor.dodge_left>0:
                for i in range(1,4):
                    point=ground-pygame.Vector2(actor.dodge_direction.x,actor.dodge_direction.y*TILT)*i*15
                    pygame.draw.ellipse(surf,(42,86,85),(point.x-16,point.y-8,32,16),1)
        direction=pygame.Vector2(1,0).rotate(actor.angle)
        side=pygame.Vector2(-direction.y,direction.x)
        for sign in (-1,1):
            stride=math.sin(actor.walk_time+sign*1.5)*5
            foot=actor.pos-direction*(8+stride)+side*sign*11
            q=camera.project(foot,4)
            pygame.draw.line(surf,(24,33,35),q,q+pygame.Vector2(direction.x,direction.y*TILT)*10,7)
        bob=math.sin(actor.walk_time*2)*1.6
        motion='fire' if actor.flash>0 else 'walk'
        if kind=='player':
            motion='reload' if actor.weapon.reloading else 'dodge' if actor.dodge_left>0 else motion
            if actor.velocity.length()<15 and motion=='walk':
                motion='idle'
        img=self.assets.actor(kind,actor.angle,weapon,scale,motion,actor.walk_time*.08)
        center=camera.project(actor.pos,17+bob)
        surf.blit(img,img.get_rect(center=center))
        if actor.hit_flash>0:
            pygame.draw.circle(surf,(241,208,157),(int(center.x),int(center.y)),int(22*scale),2)
        if actor.flash>0:
            muzzle=camera.project(actor.pos+direction*(39*scale),17)
            if quality=='High':
                glow=self.assets.glow(65,(231,148,46),True)
                surf.blit(glow,(muzzle.x-65,muzzle.y-65),special_flags=pygame.BLEND_RGB_ADD)
            tip=muzzle+pygame.Vector2(direction.x,direction.y*TILT)*19
            perpendicular=pygame.Vector2(-direction.y,direction.x)*7
            pygame.draw.polygon(surf,AMBER,[muzzle-perpendicular,tip,muzzle+perpendicular])
            pygame.draw.circle(surf,(255,248,204),muzzle,4)
        if kind!='player' and kind!='boss' and (actor.hit_flash>0 or actor.health<actor.max_health):
            ratio=max(0,actor.health/actor.max_health)
            pygame.draw.rect(surf,(23,29,29),(ground.x-20,ground.y-56,40,4),border_radius=2)
            pygame.draw.rect(surf,RED,(ground.x-20,ground.y-56,max(1,40*ratio),4),border_radius=2)

    def scene(self,surf,game,menu=False):
        camera=game.camera
        surf.fill((18,30,35))
        origin=camera.project((0,0))
        surf.blit(game.world.floor,origin)
        quality=game.settings['quality']
        for corpse in game.corpses:
            age=12-corpse['life']
            fall=min(1,age/.32)
            q=camera.project(corpse['pos'],17-12*fall)
            angle=corpse['angle']-75*(1-fall)
            img=self.assets.actor(corpse['kind'],angle,corpse['weapon'],corpse['scale'],'death',age)
            # Alpha changes only on a copy, never on the shared cached atlas.
            faded=img.copy()
            faded.fill((109,112,104,255),special_flags=pygame.BLEND_RGBA_MULT)
            faded.set_alpha(int(min(1,corpse['life']/2)*100))
            surf.blit(faded,faded.get_rect(center=q))
        for pickup in game.pickups:
            q=camera.project(pickup['pos'],8+math.sin(game.visual_time*3)*3)
            color=ACCENT if pickup['kind']=='medkit' else AMBER
            if quality=='High':
                glow=self.assets.glow(24,color,True)
                surf.blit(glow,(q.x-24,q.y-24),special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.polygon(surf,(18,33,36),[(q.x,q.y-12),(q.x+12,q.y),(q.x,q.y+12),(q.x-12,q.y)])
            pygame.draw.polygon(surf,color,[(q.x,q.y-12),(q.x+12,q.y),(q.x,q.y+12),(q.x-12,q.y)],1)
            if pickup['kind']=='medkit':
                pygame.draw.line(surf,color,(q.x-5,q.y),(q.x+5,q.y),2)
                pygame.draw.line(surf,color,(q.x,q.y-5),(q.x,q.y+5),2)
            else:
                for x in (-4,0,4):
                    pygame.draw.line(surf,color,(q.x+x,q.y-4),(q.x+x,q.y+4),2)
        objects=[(o.rect.bottom,'obstacle',o) for o in game.world.obstacles]
        objects += [(e.pos.y+e.radius*.5,'enemy',e) for e in game.enemies]
        if not menu or game.has_run:
            objects.append((game.player.pos.y+10,'player',game.player))
        for _,kind,obj in sorted(objects,key=lambda item:item[0]):
            if kind=='obstacle':
                self.obstacle(surf,camera,obj)
            elif kind=='player':
                self.actor(surf,camera,obj,'player',obj.weapon.spec.key,quality)
            else:
                self.actor(surf,camera,obj,obj.kind,obj.spec.weapon,quality)
        for e in game.enemies:
            if e.telegraph>0:
                start=camera.project(e.pos,17)
                end=camera.project(e.pos+e.aim_direction*1050,17)
                pygame.draw.line(surf,(151,63,57),start,end,1)
                if int(game.visual_time*10)%2:
                    pygame.draw.circle(surf,RED,start,5,1)
        for b in game.bullets:
            q=camera.project(b.pos,17)
            trail=b.pos-b.velocity*.024
            prev=camera.project(trail,17)
            color=AMBER if b.owner=='player' else RED
            if quality=='High':
                glow=self.assets.glow(14,color,True)
                surf.blit(glow,(q.x-14,q.y-14),special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.line(surf,tuple(int(c*.45) for c in color),prev,q,3)
            pygame.draw.line(surf,color,prev.lerp(q,.55),q,2)
            pygame.draw.circle(surf,(255,240,194) if b.owner=='player' else (255,179,140),q,2)
        game.particles.draw(surf,camera,self.assets,quality)
        for x,y in game.world.lamps:
            q=camera.project((x,y))
            head=camera.project((x,y),77)
            pygame.draw.line(surf,(22,33,36),q,head,5)
            pygame.draw.line(surf,(172,175,147),(head.x-9,head.y),(head.x+9,head.y),4)
            if quality=='High':
                glow=self.assets.glow(22,(148,133,75),True)
                surf.blit(glow,(head.x-22,head.y-22),special_flags=pygame.BLEND_RGB_ADD)
        if quality=='High':
            # Light airborne dust with parallax distinct from the ground.
            for i in range(35):
                x=(i*139+game.visual_time*(8+i%4)-camera.center.x*.12)%WIDTH
                y=(i*83+math.sin(game.visual_time*.2+i)*22-camera.center.y*.08)%HEIGHT
                pygame.draw.circle(surf,(105,119,110),(int(x),int(y)),1)
        surf.blit(self.assets.vignette,(0,0))
        if game.player.hit_flash>0 and not menu:
            self.assets.damage.set_alpha(int(min(1,game.player.hit_flash/.2)*220))
            surf.blit(self.assets.damage,(0,0))
        for f in game.floating:
            q=camera.project(f['pos'],58+(1.2-f['life'])*32)
            text=self.assets.text(f['text'],15,f['color'],'heading')
            surf.blit(text,text.get_rect(center=q))
