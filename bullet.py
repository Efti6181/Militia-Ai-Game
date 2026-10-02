from dataclasses import dataclass, field
import pygame


def segment_circle(start, end, center, radius):
    """First intersection parameter, including very fast projectiles."""
    delta = end - start
    rel = start - center
    a = delta.length_squared()
    c = rel.length_squared() - radius * radius
    if c <= 0:
        return 0.0
    if a < .00001:
        return None
    b = 2 * rel.dot(delta)
    disc = b * b - 4 * a * c
    if disc < 0:
        return None
    t = (-b - disc ** .5) / (2 * a)
    return t if 0 <= t <= 1 else None


def segment_rect(start, end, rect):
    """Slab intersection in float coordinates, returning the nearest hit."""
    d = end - start
    t0, t1 = 0.0, 1.0
    for origin, delta, low, high in ((start.x, d.x, rect.left, rect.right),
                                    (start.y, d.y, rect.top, rect.bottom)):
        if abs(delta) < 1e-9:
            if origin < low or origin > high:
                return None
        else:
            lo, hi = (low - origin) / delta, (high - origin) / delta
            if lo > hi:
                lo, hi = hi, lo
            t0, t1 = max(t0, lo), min(t1, hi)
            if t0 > t1:
                return None
    return t0


@dataclass
class Bullet:
    pos: pygame.Vector2
    velocity: pygame.Vector2
    owner: str
    damage: float
    life: float = 2.1
    critical: bool = False
    shot_id: int = 0
    prev: pygame.Vector2 = field(init=False)

    def __post_init__(self):
        self.pos = pygame.Vector2(self.pos)
        self.velocity = pygame.Vector2(self.velocity)
        self.prev = self.pos.copy()

    def step(self, dt):
        self.prev = self.pos.copy()
        self.pos += self.velocity * dt
        self.life -= dt

