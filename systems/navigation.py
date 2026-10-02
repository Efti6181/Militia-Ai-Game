import heapq
import math
import pygame
from config import WORLD_W, WORLD_H


class Navigation:
    """A* on a static clearance grid; prevents corner cutting through cover."""
    def __init__(self, obstacles, cell=48):
        self.cell = cell
        self.cols = math.ceil(WORLD_W / cell)
        self.rows = math.ceil(WORLD_H / cell)
        self.blocked = set()
        for y in range(self.rows):
            for x in range(self.cols):
                p = self.center((x, y))
                if not (28 < p.x < WORLD_W - 28 and 28 < p.y < WORLD_H - 28):
                    self.blocked.add((x, y))
                elif any(o.rect.inflate(52, 52).collidepoint(p) for o in obstacles):
                    self.blocked.add((x, y))

    def center(self, cell):
        return pygame.Vector2((cell[0] + .5) * self.cell, (cell[1] + .5) * self.cell)

    def nearest(self, point):
        node = (max(0, min(self.cols - 1, int(point[0] // self.cell))),
                max(0, min(self.rows - 1, int(point[1] // self.cell))))
        if node not in self.blocked:
            return node
        best = None
        best_d = float('inf')
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                n = node[0] + dx, node[1] + dy
                if self.valid(n) and dx * dx + dy * dy < best_d:
                    best, best_d = n, dx * dx + dy * dy
        return best

    def valid(self, node):
        return 0 <= node[0] < self.cols and 0 <= node[1] < self.rows and node not in self.blocked

    def path(self, start, goal):
        start, goal = self.nearest(start), self.nearest(goal)
        if start is None or goal is None or start == goal:
            return []
        queue = [(0, start)]
        came, cost = {}, {start: 0}
        while queue:
            _, current = heapq.heappop(queue)
            if current == goal:
                route = [current]
                while current in came:
                    current = came[current]
                    route.append(current)
                return [self.center(n) for n in reversed(route[:-1])]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
                nxt = current[0] + dx, current[1] + dy
                if not self.valid(nxt):
                    continue
                if dx and dy and (not self.valid((current[0] + dx, current[1])) or
                                  not self.valid((current[0], current[1] + dy))):
                    continue
                price = cost[current] + (1.414 if dx and dy else 1)
                if price < cost.get(nxt, float('inf')):
                    cost[nxt], came[nxt] = price, current
                    heuristic = math.hypot(nxt[0] - goal[0], nxt[1] - goal[1])
                    heapq.heappush(queue, (price + heuristic, nxt))
        return []

