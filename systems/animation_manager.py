from dataclasses import dataclass
import pygame


@dataclass
class AnimationClip:
    frames: list
    frame_seconds: float=.10
    loop: bool=True

    def sample(self,time):
        index=max(0,int(time/self.frame_seconds))
        index=index%len(self.frames) if self.loop else min(index,len(self.frames)-1)
        return index,self.frames[index]


class AnimationManager:
    """Optional horizontal square-frame sheets; procedural animation remains the fallback."""
    def __init__(self,directory):
        self.directory=directory
        self.clips={}

    def frame(self,kind,state,time):
        key=kind,state
        if key not in self.clips:
            self.clips[key]=None
            path=self.directory/f'{kind}_{state}.png'
            if path.is_file():
                try:
                    sheet=pygame.image.load(str(path)).convert_alpha()
                    size=sheet.get_height()
                    if size>0 and sheet.get_width()%size==0 and sheet.get_width()//size<=32:
                        frames=[pygame.transform.smoothscale(sheet.subsurface((x,0,size,size)),(258,258))
                                for x in range(0,sheet.get_width(),size)]
                        self.clips[key]=AnimationClip(frames,loop=state!='death')
                except (OSError,pygame.error,ValueError):
                    pass
        clip=self.clips[key]
        return clip.sample(time) if clip else None

