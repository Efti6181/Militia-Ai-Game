"""Capture real screens and measure the real update + render pipeline, without a display."""
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time

os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from game import Game,InputFrame
from enemy import Enemy
from bullet import Bullet
from config import WIDTH,HEIGHT


def capture(game,directory,name,state=None):
    if state:
        game.change_state(state)
    game.transition=0
    game.draw((910,260),False)
    pygame.image.save(game.canvas,str(directory/f'{name}.png'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path('release-check'))
    args=parser.parse_args()
    output=args.output
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        game=Game(True,directory,6181)
        game.update(1)
        capture(game,output,'menu')
        capture(game,output,'deployment','deploy')
        capture(game,output,'controls','controls')
        capture(game,output,'settings','settings')
        game.start('operation')
        game.player.pos.update(1030,850)
        game.wave.number=5
        game.wave.phase='combat'
        game.wave.pending=[]
        game.wave.spawn_timer=99
        for kind,pos in [('soldier',(760,730)),('shotgun',(1270,700)),('heavy',(1550,930)),
                         ('sniper',(1240,350)),('runner',(730,1050)),('boss',(1340,500)),('soldier',(1130,590))]:
            if game.world.free(pos):
                e=Enemy(kind,pos,5,game.rng)
                e.age=3
                game.enemies.append(e)
        game.stats.update(score=5400,kills=31,shots=100,hits=78,time=228)
        game.ui.score_display=5400
        game.announcement_left=0
        game.player.armor=53
        game.camera.follow(game.player.pos,pygame.Vector2(1270,700),0,instant=True)
        game.player.invulnerable=999
        for _ in range(68):
            game.update(1/60,InputFrame(pygame.Vector2(),pygame.Vector2(1270,700),True))
        capture(game,output,'gameplay')
        game.player.weapon.ammo=3
        game.player.weapon.reload()
        capture(game,output,'reload')
        capture(game,output,'pause','pause')
        game.wave.choices=['damage','health','reload']
        capture(game,output,'upgrades','upgrade')
        game.player.health=0
        game.finish(False)
        capture(game,output,'game_over')
        game.player.health=173
        game.enemies.clear()
        game.bullets.clear()
        game.wave.number=10
        game.wave.phase='complete'
        game.stats.update(score=22840,kills=152,shots=687,hits=521,time=961,precision=9)
        game.finish(True)
        capture(game,output,'victory')
        # Live stress scene: 24 agents with navigation, gunfire and effects enabled.
        # Invulnerability is restricted to this QA harness, not normal gameplay.
        game.start('survival')
        game.wave.number=10
        game.wave.phase='combat'
        game.wave.pending=['soldier']
        game.wave.spawn_timer=999
        game.player.pos.update(1000,730)
        game.player.invulnerable=999
        for i in range(24):
            kind=['soldier','shotgun','sniper','runner','heavy','boss'][i%6]
            game.spawn_enemy(kind)
        timings=[]
        for frame in range(420):
            start=time.perf_counter()
            if frame%60==0:
                game.player.weapon.refill()
            target=min(game.enemies,key=lambda e:e.pos.distance_squared_to(game.player.pos))
            movement=pygame.Vector2(math.cos(frame/50),math.sin(frame/50))*.5
            inputs=InputFrame(movement,target.pos.copy(),True)
            game.mouse=game.camera.project(target.pos,17)
            game.update(1/60,inputs)
            game.draw()
            if frame>=60:
                timings.append((time.perf_counter()-start)*1000)
            assert len(game.particles.items)<=650
            assert 0<=game.stats['hits']<=game.stats['shots']
            assert game.world.free(game.player.pos,game.player.radius-.1)
            if frame%30==0:
                assert all(game.world.free(e.pos,e.radius-.1) for e in game.enemies)
        ordered=sorted(timings)
        report={'pygame':pygame.version.ver,'python':sys.version.split()[0],
                'renderer':'SDL dummy; software rendering, logical 1400x800',
                'quality':game.settings['quality'],'starting_enemies':24,'simulation_hz':120,
                'frames_measured':len(timings),'mean_frame_ms':round(statistics.mean(timings),3),
                'p95_frame_ms':round(ordered[int(len(ordered)*.95)],3),
                'equivalent_uncapped_fps':round(1000/statistics.mean(timings),1),
                'actual_play_is_capped_at_fps':60,
                'stress_scene_survived_without_crashes':True,'stress_kills':game.stats['kills'],
                'note':'A container measurement, not a guarantee for every PC; stress player is invulnerable.'}
        capture(game,output,'stress_combat')
        (output/'benchmark.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))
        # Long run: every type spawns, ordinary damage works, and defeat reaches its screen.
        game.start('operation')
        for _ in range(60*180):
            if game.state!='playing':
                break
            game.update(1/60,InputFrame(aim=game.player.pos+pygame.Vector2(0,-100)))
        assert game.state=='game_over','Stationary unarmed player should eventually lose to real combat.'
        print(f"Live loss path: wave {game.wave.number}, {game.stats['time']:.1f}s, {len(game.enemies)} hostiles.")
        game.close()
    pygame.quit()


if __name__=='__main__':
    main()
