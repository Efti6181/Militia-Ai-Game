import math
import pygame
from config import WIDTH, HEIGHT, WORLD_W, WORLD_H, TILT


class Camera:
    def __init__(self, rng):
        self.center = pygame.Vector2(WORLD_W / 2, WORLD_H * TILT / 2)
        self.offset = pygame.Vector2()
        self.trauma = 0
        self.rng = rng

    def follow(self, position, aim, dt, shake=True, instant=False):
        look = aim - position
        if look.length_squared() > 1:
            look.scale_to_length(min(85, look.length() * .13))
        target = pygame.Vector2(position.x + look.x, (position.y + look.y) * TILT)
        target.x = max(WIDTH / 2 - 60, min(WORLD_W - WIDTH / 2 + 60, target.x))
        target.y = max(HEIGHT / 2 - 60, min(WORLD_H * TILT - HEIGHT / 2 + 60, target.y))
        self.center = target if instant else self.center.lerp(target, 1 - math.exp(-6 * dt))
        self.trauma = max(0, self.trauma - dt * 1.8)
        strength = 10 * self.trauma * self.trauma if shake else 0
        self.offset.update(self.rng.uniform(-strength, strength), self.rng.uniform(-strength, strength))

    def kick(self, amount):
        self.trauma = min(1, self.trauma + amount)

    def project(self, position, height=0):
        return pygame.Vector2(position[0] - self.center.x + WIDTH / 2 + self.offset.x,
                              position[1] * TILT - self.center.y + HEIGHT / 2 + self.offset.y - height)

    def unproject(self, position, height=0):
        return pygame.Vector2(position[0] + self.center.x - WIDTH / 2 - self.offset.x,
                              (position[1] + self.center.y - HEIGHT / 2 - self.offset.y + height) / TILT)

