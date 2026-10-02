"""Run the game from any working directory: python /path/to/AI_Militia/main.py."""
import argparse
import os
from pathlib import Path
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(description='AI Militia: Combat Zone / Pygame 2.5D shooter')
    parser.add_argument('--headless',action='store_true',help='Use dummy video/audio devices for automated checks')
    parser.add_argument('--frames',type=int,default=0,help='Exit after this many frames (0 = unlimited)')
    parser.add_argument('--demo',choices=['menu','game'],help='Render a deterministic preview scene')
    parser.add_argument('--capture',type=Path,help='Save the final logical-resolution frame as a PNG')
    parser.add_argument('--save-dir',type=Path,help='Override the user save directory')
    parser.add_argument('--seed',type=int,help='Random seed for reproducible debugging')
    args=parser.parse_args()
    if args.headless:
        os.environ['SDL_VIDEODRIVER']='dummy'
        os.environ['SDL_AUDIODRIVER']='dummy'
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
    try:
        import pygame
        from game import Game,InputFrame
    except ModuleNotFoundError as error:
        print(f'Missing dependency: {error.name}. Run: python -m pip install -r requirements.txt')
        return 1
    # Previews must not replace a real user's active checkpoint.
    temp=tempfile.TemporaryDirectory(prefix='militia-preview-') if args.demo and not args.save_dir else None
    game=Game(args.headless,args.save_dir or (temp.name if temp else None),args.seed)
    if args.demo=='game':
        game.start('operation')
        game.player.pos.update(1030,850)
        game.wave.number=4
        game.wave.phase='combat'
        game.wave.pending=[]
        game.wave.spawn_timer=99
        from enemy import Enemy
        for kind,pos in [('soldier',(760,740)),('shotgun',(1270,700)),('heavy',(1550,935)),
                         ('sniper',(1240,350)),('runner',(730,1030)),('soldier',(1130,590))]:
            if game.world.free(pos):
                game.enemies.append(Enemy(kind,pos,4,game.rng))
        game.player.armor=53
        game.stats.update(score=2450,kills=18,shots=78,hits=51,time=142)
        game.ui.score_display=2450
        game.camera.follow(game.player.pos,pygame.Vector2(1270,700),0,instant=True)
        game.announcement_left=0
    frame=0
    try:
        while game.running:
            dt=1/60 if args.headless else min(.1,game.clock.tick(60)/1000)
            game.handle_events(pygame.event.get())
            if not game.running:
                break
            inputs=game.poll_input()
            if args.demo=='game':
                inputs=InputFrame(pygame.Vector2(),pygame.Vector2(1270,700),True,False)
                game.mouse=game.camera.project(inputs.aim,17)
            game.update(dt,inputs)
            game.draw()
            frame+=1
            if args.frames and frame>=args.frames:
                break
        if args.capture:
            args.capture.parent.mkdir(parents=True,exist_ok=True)
            pygame.image.save(game.canvas,str(args.capture))
        game.close()
    finally:
        pygame.quit()
        if temp:
            temp.cleanup()
    return 0


if __name__=='__main__':
    sys.exit(main())

