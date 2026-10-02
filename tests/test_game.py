"""Behavioral checks using real Pygame surfaces and a deterministic headless simulation."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from game import Game,InputFrame
from config import DEFAULT_SETTINGS,WIDTH,HEIGHT,ACCENT
from enemy import Enemy,ENEMIES
from bullet import Bullet,segment_circle,segment_rect
from world import SpatialHash
from systems.save_manager import SaveManager,clean_settings
from systems.animation_manager import AnimationManager


class GameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.game=Game(True,cls.temp.name,6181)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()
        cls.temp.cleanup()

    def setUp(self):
        self.g=self.game
        self.g.settings.clear()
        self.g.settings.update(copy.deepcopy(DEFAULT_SETTINGS))
        self.g.start('operation')
        self.g.wave.phase='combat'
        self.g.wave.pending=['soldier']
        self.g.wave.spawn_timer=999
        self.g.transition=0

    def enemy(self,kind='soldier',pos=(1000,550)):
        e=Enemy(kind,pos,self.g.wave.number,self.g.rng)
        self.g.enemies.append(e)
        self.reindex()
        return e

    def reindex(self):
        self.g.enemy_spatial=SpatialHash()
        for e in self.g.enemies:
            self.g.enemy_spatial.add(e,pygame.Rect(e.pos.x-e.radius,e.pos.y-e.radius,e.radius*2,e.radius*2))

    def test_original_health_and_enemy_archetypes_retained(self):
        self.assertEqual(self.g.player.health,500)
        self.assertEqual(len(self.g.world.obstacles[:6]),6)
        for kind in ('soldier','shotgun','sniper'):
            self.assertIn(kind,ENEMIES)

    def test_movement_is_independent_of_render_rate(self):
        positions=[]
        for fps in (30,60,120):
            self.g.start()
            self.g.wave.timer=999
            self.g.player.pos.update(1000,1100)
            inputs=InputFrame(pygame.Vector2(1,0),pygame.Vector2(1500,1100))
            for _ in range(fps):
                self.g.update(1/fps,inputs)
            positions.append(self.g.player.pos.copy())
        for pos in positions[1:]:
            self.assertLess(pos.distance_to(positions[0]),.1)

    def test_diagonal_movement_is_normalized(self):
        distances=[]
        for direction in (pygame.Vector2(1,0),pygame.Vector2(1,1)):
            self.g.start()
            origin=pygame.Vector2(1000,1000)
            self.g.player.pos=origin.copy()
            for _ in range(24):
                self.g.player.update(1/120,direction,origin+pygame.Vector2(0,-300),False,self.g.world,1)
            distances.append(self.g.player.pos.distance_to(origin))
        self.assertAlmostEqual(distances[0],distances[1],places=4)

    def test_characters_cannot_cross_obstacles_even_with_large_delta(self):
        for o in self.g.world.obstacles:
            origin=pygame.Vector2(o.rect.left-40,o.rect.centery)
            if not self.g.world.free(origin,19):
                continue
            result=self.g.world.move(origin,pygame.Vector2(500,0),19)
            self.assertLessEqual(result.x,o.rect.left-18.95)
            self.assertFalse(o.rect.collidepoint(result))

    def test_rotation_never_changes_collision_radius(self):
        p=self.g.player
        for i in range(72):
            aim=p.pos+pygame.Vector2(100,0).rotate(i*5)
            p.update(1/60,pygame.Vector2(),aim,False,self.g.world,1)
            self.assertEqual(p.radius,19)

    def test_player_enemy_bodies_resolve_overlap(self):
        self.g.player.pos.update(1000,1000)
        enemy=self.enemy(pos=(1000,1010))
        self.g.resolve_actor_contacts()
        self.assertGreaterEqual(self.g.player.pos.distance_to(enemy.pos),self.g.player.radius+enemy.radius)
        self.assertTrue(self.g.world.free(self.g.player.pos,self.g.player.radius-.1))
        self.assertTrue(self.g.world.free(enemy.pos,enemy.radius-.1))

    def test_sprint_and_dodge_consume_stamina(self):
        p=self.g.player
        p.pos.update(1000,1100)
        p.update(.1,pygame.Vector2(0,-1),pygame.Vector2(1000,300),True,self.g.world,1)
        self.assertLess(p.stamina,100)
        self.assertTrue(p.sprinting)
        stamina=p.stamina
        self.assertTrue(p.dodge(pygame.Vector2(1,0)))
        self.assertLess(p.stamina,stamina)
        self.assertFalse(p.dodge(pygame.Vector2(1,0)))
        self.assertFalse(p.take_damage(100,p.pos+pygame.Vector2(5,0)))

    def test_reload_and_switch_cancel(self):
        p=self.g.player
        w=p.weapon
        w.ammo=2
        reserve=w.reserve
        self.assertTrue(w.reload())
        w.update(w.spec.reload+.01)
        self.assertEqual(w.ammo,30)
        self.assertEqual(w.reserve,reserve-28)
        w.ammo=3
        self.assertTrue(w.reload())
        p.switch(0)
        self.assertEqual(w.reload_left,0)
        p.weapon.ammo=0
        p.weapon.reserve=0
        self.assertTrue(p.weapon.reload())
        p.weapon.update(2)
        self.assertEqual(p.weapon.ammo,p.weapon.spec.magazine)

    def test_all_weapons_fire_and_shotgun_has_eight_pellets(self):
        p=self.g.player
        p.pos.update(1000,1100)
        p.angle=-90
        for i in range(4):
            p.switch(i)
            before=len(self.g.bullets)
            ammo=p.weapon.ammo
            self.g.fire()
            self.assertEqual(ammo-1,p.weapon.ammo)
            self.assertEqual(len(self.g.bullets)-before,8 if i==2 else 1)
        self.assertEqual(self.g.stats['shots'],4)

    def test_barrel_cannot_shoot_through_cover(self):
        o=self.g.world.obstacles[4]
        p=self.g.player
        p.pos.update(o.rect.left-p.radius-.1,o.rect.centery)
        p.angle=0
        self.g.fire()
        self.assertEqual(len(self.g.bullets),0)
        self.assertEqual(p.weapon.ammo,29)

    def test_swept_collision_hits_a_target_between_frames(self):
        e=self.enemy(pos=(1000,600))
        self.g.bullets=[Bullet(pygame.Vector2(1000,650),pygame.Vector2(0,-4000),'player',40,shot_id=1)]
        self.g.stats['shots']=1
        self.g.update_bullets(1/30)
        self.assertLess(e.health,e.max_health)
        self.assertEqual(self.g.stats['hits'],1)
        self.assertFalse(self.g.bullets)

    def test_nearest_wall_blocks_projectiles_before_enemies(self):
        o=self.g.world.obstacles[4]
        y=o.rect.centery
        e=self.enemy(pos=(o.rect.right+100,y))
        self.g.bullets=[Bullet(pygame.Vector2(o.rect.left-100,y),pygame.Vector2(4000,0),'player',200,shot_id=1)]
        self.g.update_bullets(.1)
        self.assertEqual(e.health,e.max_health)
        self.assertFalse(self.g.bullets)

    def test_each_shot_counts_accuracy_once_even_with_pellets(self):
        e=self.enemy(kind='boss',pos=(1000,600))
        self.g.bullets=[Bullet(pygame.Vector2(1000,630),pygame.Vector2(0,-1500),'player',23,shot_id=1) for _ in range(8)]
        self.g.stats['shots']=1
        self.g.update_bullets(1/60)
        self.assertEqual(self.g.stats['hits'],1)
        self.assertAlmostEqual(e.health,e.max_health-8*23)

    def test_sniper_has_a_visible_warning_before_firing(self):
        self.g.player.pos.update(1000,1150)
        e=self.enemy('sniper',(1000,560))
        e.age=2
        e.cooldown=0
        e.update(.01,self.g)
        self.assertGreater(e.telegraph,0)
        self.assertEqual(len(self.g.bullets),0)
        e.update(1,self.g)
        self.assertEqual(len(self.g.bullets),1)

    def test_low_health_enemy_takes_cover(self):
        self.g.player.pos.update(1000,1150)
        e=self.enemy(pos=(1000,600))
        e.health=e.max_health*.2
        e.age=2
        e.update(.01,self.g)
        self.assertEqual(e.state,'TAKE_COVER')
        self.assertTrue(e.has_retreated)

    def test_astar_routes_around_the_central_barrier(self):
        start,goal=pygame.Vector2(1020,830),pygame.Vector2(750,830)
        self.assertFalse(self.g.world.clear_line(start,goal))
        route=self.g.world.nav.path(start,goal)
        self.assertTrue(route)
        for a,b in zip([start]+route,route+[goal]):
            self.assertTrue(self.g.world.clear_line(a,b,18))

    def test_pause_freezes_all_simulation_timers(self):
        self.g.player.weapon.ammo=1
        self.g.player.weapon.reload()
        self.enemy()
        self.g.pause()
        before=self.g.snapshot()
        self.g.update(2,InputFrame(pygame.Vector2(1,0),pygame.Vector2(100,100),True))
        self.assertEqual(before,self.g.snapshot())
        self.g.action('settings')
        self.g.update(2)
        self.assertEqual(before,self.g.snapshot())
        self.g.action('back')
        self.assertEqual(self.g.state,'pause')
        self.g.pause()
        self.assertEqual(self.g.state,'playing')

    def test_wave_completion_upgrade_and_refill(self):
        self.g.wave.pending=[]
        self.g.player.weapon.ammo=0
        self.g.step(1/120,InputFrame())
        self.assertEqual(self.g.state,'upgrade')
        self.assertEqual(self.g.player.weapon.ammo,30)
        self.assertEqual(len(self.g.wave.choices),3)
        damage=self.g.player.damage
        self.g.action(('upgrade','damage'))
        self.assertGreater(self.g.player.damage,damage)
        self.assertEqual(self.g.wave.number,2)
        self.assertEqual(self.g.state,'playing')

    def test_final_wave_victory_and_survival_continues(self):
        self.g.wave.number=10
        self.g.wave.pending=[]
        self.g.step(1/120,InputFrame())
        self.assertEqual(self.g.state,'victory')
        self.assertIsNone(self.g.save.data['checkpoint'])
        self.g.action('main_menu')
        self.g.close()
        self.assertIsNone(self.g.save.data['checkpoint'])
        self.g.running=True
        self.g.start('survival')
        self.g.wave.number=10
        self.g.wave.phase='combat'
        self.g.wave.pending=[]
        self.g.step(1/120,InputFrame())
        self.assertEqual(self.g.state,'upgrade')
        self.g.action(('upgrade',None))
        self.assertEqual(self.g.wave.number,11)

    def test_death_retry_resets_position_health_and_entities(self):
        self.g.player.health=0
        self.g.step(1/120,InputFrame())
        self.assertEqual(self.g.state,'game_over')
        self.g.action('restart')
        self.assertEqual(self.g.player.health,500)
        self.assertEqual(self.g.player.pos,pygame.Vector2(1000,1230))
        self.assertFalse(self.g.enemies)
        self.assertEqual(self.g.stats['kills'],0)

    def test_checkpoint_round_trip_restores_combat(self):
        self.g.wave.spawn_timer=.6
        self.g.player.pos.update(1000,1100)
        self.g.player.health=273
        self.g.stats.update(score=3900,kills=12,shots=20,hits=11)
        self.enemy('heavy',(1000,350))
        self.g.player.weapon.ammo=3
        self.g.bullets=[Bullet(pygame.Vector2(1000,500),pygame.Vector2(0,700),'enemy',20)]
        expected=self.g.snapshot()
        self.g.save_checkpoint()
        self.g.player=type(self.g.player)()
        self.g.enemies=[]
        self.assertTrue(self.g.restore())
        actual=self.g.snapshot()
        self.assertEqual(expected,actual)

    def test_corrupted_and_wrong_shape_saves_are_safe(self):
        for data in ('{broken','null','[]','{"version":1,"settings":{"resolution":[-1,5],"master":999}}'):
            self.g.save.path.write_text(data,encoding='utf-8')
            loaded=SaveManager(self.temp.name)
            self.assertGreaterEqual(loaded.settings['master'],0)
            self.assertLessEqual(loaded.settings['master'],1)
            self.assertIn(tuple(loaded.settings['resolution']),[(1280,720),(1400,800),(1600,900),(1920,1080)])
        self.g.save.data['checkpoint']={'version':1,'player':None}
        self.assertFalse(self.g.restore())
        self.assertIsNone(self.g.save.data['checkpoint'])

    def test_malformed_checkpoint_fields_never_crash_or_partially_restore(self):
        baseline=self.g.snapshot()
        mutations=[('player',None),('enemies',None),('bullets',[None]),('stats',[]),
                   ('pickups',[None]),('hit_ids',None),('wave',{'mode':'unknown'})]
        for key,bad in mutations:
            invalid=copy.deepcopy(baseline)
            invalid[key]=bad
            self.g.save.data['checkpoint']=invalid
            self.assertFalse(self.g.restore(),key)
            self.assertEqual(self.g.player.pos,pygame.Vector2(baseline['player']['pos']))

    def test_settings_persist_and_volumes_stay_bounded(self):
        self.g.change_setting('shake',1)
        for _ in range(15):
            self.g.change_setting('master',1)
        self.g.change_setting('difficulty',1)
        self.g.change_setting('sensitivity',1)
        loaded=SaveManager(self.temp.name)
        self.assertFalse(loaded.settings['shake'])
        self.assertEqual(loaded.settings['master'],1)
        self.assertEqual(loaded.settings['difficulty'],'Veteran')
        self.assertEqual(loaded.settings['sensitivity'],1.1)

    def test_projection_and_letterboxing_are_invertible(self):
        point=pygame.Vector2(1117,687)
        projected=self.g.camera.project(point,17)
        self.assertLess(self.g.camera.unproject(projected,17).distance_to(point),1e-6)
        self.g.resize_viewport((1024,768))
        q=(self.g.viewport.x+self.g.viewport.w*.5,self.g.viewport.y+self.g.viewport.h*.5)
        self.assertLess(self.g.logical_mouse(q).distance_to((WIDTH/2,HEIGHT/2)),.01)
        self.g.resize_viewport(self.g.display.get_size())

    def test_every_screen_renders_and_buttons_stay_in_bounds(self):
        self.g.wave.choices=['damage','reload','armor']
        for state in ('menu','deploy','settings','controls','credits','pause','playing','upgrade','game_over','victory'):
            self.g.state=state
            self.g.draw((700,400),False)
            self.assertEqual(self.g.canvas.get_size(),(WIDTH,HEIGHT))
            for button in self.g.ui.buttons:
                self.assertTrue(self.g.canvas.get_rect().contains(button.rect),state+': '+button.label)

    def test_menu_click_and_keyboard_controls(self):
        self.g.state='menu'
        self.g.draw((100,377),False)
        self.g.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(100,377))])
        self.assertEqual(self.g.state,'deploy')
        self.g.start()
        self.g.handle_events([pygame.event.Event(pygame.KEYDOWN,key=pygame.K_4)])
        self.assertEqual(self.g.player.selected,3)
        self.g.handle_events([pygame.event.Event(pygame.MOUSEWHEEL,y=1,x=0)])
        self.assertEqual(self.g.player.selected,2)
        self.g.handle_events([pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE)])
        self.assertEqual(self.g.state,'pause')

    def test_audio_missing_device_does_not_block_play(self):
        enabled=self.g.audio.enabled
        self.g.audio.enabled=False
        self.g.audio.play('rifle')
        self.g.player.pos.update(1000,1100)
        self.g.player.angle=-90
        self.g.fire()
        self.assertEqual(len(self.g.bullets),1)
        self.g.audio.enabled=enabled

    def test_animation_override_and_invalid_asset_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            manager=AnimationManager(path)
            self.assertIsNone(manager.frame('player','idle',0))
            sheet=pygame.Surface((64,32),pygame.SRCALPHA)
            sheet.fill((255,0,0),pygame.Rect(0,0,32,32))
            sheet.fill((0,255,0),pygame.Rect(32,0,32,32))
            pygame.image.save(sheet,str(path/'player_walk.png'))
            self.assertEqual(manager.frame('player','walk',.11)[0],1)
            (path/'soldier_walk.png').write_text('corrupt')
            self.assertIsNone(manager.frame('soldier','walk',0))


class GeometryTests(unittest.TestCase):
    def test_first_intersection_and_zero_vectors(self):
        a,b=pygame.Vector2(0,0),pygame.Vector2(100,0)
        self.assertAlmostEqual(segment_circle(a,b,pygame.Vector2(50,0),10),.4)
        self.assertAlmostEqual(segment_rect(a,b,pygame.Rect(60,-5,20,10)),.6)
        self.assertIsNone(segment_circle(a,a,pygame.Vector2(10,0),1))
        self.assertIsNone(segment_rect(a,b,pygame.Rect(20,20,30,30)))
        self.assertEqual(segment_circle(a,a,a,10),0)


if __name__=='__main__':
    unittest.main(verbosity=2)
