"""Planarity – drag nodes to untangle a planar graph."""

import math
import random
import sys
from collections import deque

import pygame

# ── Constants ────────────────────────────────────────────────────────────────

WIDTH, HEIGHT = 900, 700
HUD_HEIGHT = 50
PLAY_AREA = pygame.Rect(10, HUD_HEIGHT + 10, WIDTH - 20, HEIGHT - HUD_HEIGHT - 20)
FPS = 60

BG_COLOR = (18, 18, 30)
EDGE_COLOR = (60, 100, 180)
EDGE_CROSS_COLOR = (200, 50, 50)
NODE_COLOR = (120, 180, 255)
NODE_DRAG_COLOR = (255, 220, 80)
NODE_GLOW_COLOR = (80, 255, 120)
CROSS_DOT_COLOR = (255, 60, 60)
HUD_COLOR = (200, 200, 220)
OVERLAY_COLOR = (30, 200, 80)

LEVELS = [
    {"nodes": 5, "remove_frac": 0.35},
    {"nodes": 7, "remove_frac": 0.30},
    {"nodes": 9, "remove_frac": 0.25},
    {"nodes": 12, "remove_frac": 0.20},
    {"nodes": 15, "remove_frac": 0.18},
    {"nodes": 18, "remove_frac": 0.15},
    {"nodes": 22, "remove_frac": 0.12},
    {"nodes": 27, "remove_frac": 0.10},
    {"nodes": 33, "remove_frac": 0.08},
    {"nodes": 40, "remove_frac": 0.05},
]

# ── Geometry helpers ─────────────────────────────────────────────────────────


def cross2d(o, a, b):
    """2D cross product of vectors OA and OB."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def on_segment(p, q, r):
    """Check if point q lies on segment pr (collinear assumed)."""
    return (
        min(p[0], r[0]) <= q[0] <= max(p[0], r[0])
        and min(p[1], r[1]) <= q[1] <= max(p[1], r[1])
    )


def segments_intersect(p1, p2, p3, p4):
    """Return True if segment p1-p2 properly intersects p3-p4."""
    d1 = cross2d(p3, p4, p1)
    d2 = cross2d(p3, p4, p2)
    d3 = cross2d(p1, p2, p3)
    d4 = cross2d(p1, p2, p4)

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
        (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
    ):
        return True

    if d1 == 0 and on_segment(p3, p1, p4):
        return True
    if d2 == 0 and on_segment(p3, p2, p4):
        return True
    if d3 == 0 and on_segment(p1, p3, p2):
        return True
    if d4 == 0 and on_segment(p1, p4, p2):
        return True
    return False


def intersection_point(p1, p2, p3, p4):
    """Compute the intersection point of two segments (assumes they cross)."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-10:
        return ((x1 + x2 + x3 + x4) / 4, (y1 + y2 + y3 + y4) / 4)
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    ix = x1 + t * (x2 - x1)
    iy = y1 + t * (y2 - y1)
    return (ix, iy)


# ── Graph generation ─────────────────────────────────────────────────────────


def generate_planar_graph(num_nodes, remove_frac):
    """Generate a planar graph via incremental face subdivision.

    Returns (edges, solution_positions).
    """
    # Start with a triangle
    cx, cy = PLAY_AREA.centerx, PLAY_AREA.centery
    r = min(PLAY_AREA.width, PLAY_AREA.height) * 0.4
    positions = []
    for i in range(3):
        angle = 2 * math.pi * i / 3 - math.pi / 2
        positions.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

    edges = {(0, 1), (1, 2), (0, 2)}
    # Faces as sorted tuples of 3 node indices
    faces = [(0, 1, 2)]

    for n in range(3, num_nodes):
        # Pick a random face
        fi = random.randint(0, len(faces) - 1)
        a, b, c = faces[fi]
        # Place new node at centroid with jitter
        ax, ay = positions[a]
        bx, by = positions[b]
        ccx, ccy = positions[c]
        nx = (ax + bx + ccx) / 3 + random.uniform(-r * 0.05, r * 0.05)
        ny = (ay + by + ccy) / 3 + random.uniform(-r * 0.05, r * 0.05)
        positions.append((nx, ny))

        # Add edges to face vertices
        edges.add((min(a, n), max(a, n)))
        edges.add((min(b, n), max(b, n)))
        edges.add((min(c, n), max(c, n)))

        # Replace face with 3 new faces
        del faces[fi]
        faces.append(tuple(sorted((a, b, n))))
        faces.append(tuple(sorted((a, c, n))))
        faces.append(tuple(sorted((b, c, n))))

    # Edge thinning: remove non-bridge edges
    edges_list = list(edges)
    random.shuffle(edges_list)
    num_remove = int(len(edges_list) * remove_frac)
    removed = 0
    for e in edges_list:
        if removed >= num_remove:
            break
        # Check if removing this edge disconnects the graph
        test_edges = edges - {e}
        if is_connected(num_nodes, test_edges):
            # Also ensure minimum degree 2 for all nodes
            deg_a = sum(1 for u, v in test_edges if u == e[0] or v == e[0])
            deg_b = sum(1 for u, v in test_edges if u == e[1] or v == e[1])
            if deg_a >= 2 and deg_b >= 2:
                edges = test_edges
                removed += 1

    return list(edges), positions


def is_connected(n, edges):
    """BFS connectivity check."""
    if n == 0:
        return True
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    visited = [False] * n
    queue = deque([0])
    visited[0] = True
    count = 1
    while queue:
        node = queue.popleft()
        for nb in adj[node]:
            if not visited[nb]:
                visited[nb] = True
                count += 1
                queue.append(nb)
    return count == n


def scramble_positions(num_nodes, edges):
    """Randomize positions ensuring some crossings exist."""
    margin = 30
    for _ in range(100):
        positions = []
        for _ in range(num_nodes):
            x = random.uniform(PLAY_AREA.left + margin, PLAY_AREA.right - margin)
            y = random.uniform(PLAY_AREA.top + margin, PLAY_AREA.bottom - margin)
            positions.append((x, y))
        crossings = count_crossings(edges, positions)
        if crossings >= max(3, len(edges) // 4):
            return positions
    return positions


def count_crossings(edges, positions):
    """Count the number of edge crossings."""
    count = 0
    for i in range(len(edges)):
        u1, v1 = edges[i]
        p1, p2 = positions[u1], positions[v1]
        for j in range(i + 1, len(edges)):
            u2, v2 = edges[j]
            if u1 == u2 or u1 == v2 or v1 == u2 or v1 == v2:
                continue
            p3, p4 = positions[u2], positions[v2]
            if segments_intersect(p1, p2, p3, p4):
                count += 1
    return count


def find_crossings(edges, positions):
    """Return set of crossing edge indices and list of crossing points."""
    crossing_edges = set()
    crossing_points = []
    for i in range(len(edges)):
        u1, v1 = edges[i]
        p1, p2 = positions[u1], positions[v1]
        for j in range(i + 1, len(edges)):
            u2, v2 = edges[j]
            if u1 == u2 or u1 == v2 or v1 == u2 or v1 == v2:
                continue
            p3, p4 = positions[u2], positions[v2]
            if segments_intersect(p1, p2, p3, p4):
                crossing_edges.add(i)
                crossing_edges.add(j)
                crossing_points.append(intersection_point(p1, p2, p3, p4))
    return crossing_edges, crossing_points


def find_crossings_incident(edges, positions, node_idx, crossing_edges, crossing_points):
    """Incrementally update crossings for edges incident to node_idx."""
    # Build set of edge indices incident to node_idx
    incident = set()
    for i, (u, v) in enumerate(edges):
        if u == node_idx or v == node_idx:
            incident.add(i)

    # Remove old crossing info for incident edges
    new_crossing_edges = set()
    new_crossing_points = []

    for i in range(len(edges)):
        u1, v1 = edges[i]
        p1, p2 = positions[u1], positions[v1]
        for j in range(i + 1, len(edges)):
            if i not in incident and j not in incident:
                # Keep old result for non-incident pairs
                continue
            u2, v2 = edges[j]
            if u1 == u2 or u1 == v2 or v1 == u2 or v1 == v2:
                continue
            p3, p4 = positions[u2], positions[v2]
            if segments_intersect(p1, p2, p3, p4):
                new_crossing_edges.add(i)
                new_crossing_edges.add(j)
                new_crossing_points.append(intersection_point(p1, p2, p3, p4))

    # Merge: keep non-incident old crossings
    final_edges = set()
    final_points = []

    # Re-check all non-incident pairs from old data
    for i in range(len(edges)):
        if i in incident:
            continue
        u1, v1 = edges[i]
        p1, p2 = positions[u1], positions[v1]
        for j in range(i + 1, len(edges)):
            if j in incident:
                continue
            u2, v2 = edges[j]
            if u1 == u2 or u1 == v2 or v1 == u2 or v1 == v2:
                continue
            p3, p4 = positions[u2], positions[v2]
            if segments_intersect(p1, p2, p3, p4):
                final_edges.add(i)
                final_edges.add(j)
                final_points.append(intersection_point(p1, p2, p3, p4))

    final_edges |= new_crossing_edges
    final_points.extend(new_crossing_points)
    return final_edges, final_points


# ── Game class ───────────────────────────────────────────────────────────────


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Planarity")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 20, bold=True)
        self.big_font = pygame.font.SysFont("monospace", 48, bold=True)
        self.small_font = pygame.font.SysFont("monospace", 14)

        self.level = 0
        self.dragging = None
        self.solved = False
        self.solve_time = 0
        self.load_level()

    def load_level(self):
        cfg = LEVELS[self.level]
        self.num_nodes = cfg["nodes"]
        self.edges, self.solution = generate_planar_graph(
            self.num_nodes, cfg["remove_frac"]
        )
        self.positions = scramble_positions(self.num_nodes, self.edges)
        self.crossing_edges, self.crossing_points = find_crossings(
            self.edges, self.positions
        )
        self.num_crossings = len(self.crossing_points)
        self.solved = False
        self.dragging = None
        self.node_radius = max(6, int(18 - self.num_nodes * 0.25))

    def node_at(self, mx, my):
        """Find node under mouse, preferring topmost (last drawn)."""
        hit_r = self.node_radius + 4
        for i in range(self.num_nodes - 1, -1, -1):
            dx = mx - self.positions[i][0]
            dy = mx - self.positions[i][1]
            dx = mx - self.positions[i][0]
            dy = my - self.positions[i][1]
            if dx * dx + dy * dy <= hit_r * hit_r:
                return i
        return None

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_r:
                        self.load_level()
                    elif event.key == pygame.K_n and self.solved:
                        if self.level < len(LEVELS) - 1:
                            self.level += 1
                            self.load_level()

                elif event.type == pygame.MOUSEBUTTONDOWN and not self.solved:
                    if event.button == 1:
                        node = self.node_at(*event.pos)
                        if node is not None:
                            self.dragging = node

                elif event.type == pygame.MOUSEBUTTONUP:
                    if self.dragging is not None:
                        # Full recheck on release
                        self.crossing_edges, self.crossing_points = find_crossings(
                            self.edges, self.positions
                        )
                        self.num_crossings = len(self.crossing_points)
                        if self.num_crossings == 0 and not self.solved:
                            self.solved = True
                            self.solve_time = pygame.time.get_ticks()
                        self.dragging = None

                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging is not None:
                        mx = max(PLAY_AREA.left, min(event.pos[0], PLAY_AREA.right))
                        my = max(PLAY_AREA.top, min(event.pos[1], PLAY_AREA.bottom))
                        self.positions[self.dragging] = (mx, my)
                        # Incremental crossing update
                        self.crossing_edges, self.crossing_points = (
                            find_crossings_incident(
                                self.edges,
                                self.positions,
                                self.dragging,
                                self.crossing_edges,
                                self.crossing_points,
                            )
                        )
                        self.num_crossings = len(self.crossing_points)

            self.draw(dt)

        pygame.quit()

    def draw(self, dt):
        self.screen.fill(BG_COLOR)

        # ── Edges ──
        for i, (u, v) in enumerate(self.edges):
            color = EDGE_CROSS_COLOR if i in self.crossing_edges else EDGE_COLOR
            p1 = (int(self.positions[u][0]), int(self.positions[u][1]))
            p2 = (int(self.positions[v][0]), int(self.positions[v][1]))
            pygame.draw.line(self.screen, color, p1, p2, 2)

        # ── Crossing dots ──
        for pt in self.crossing_points:
            pygame.draw.circle(
                self.screen, CROSS_DOT_COLOR, (int(pt[0]), int(pt[1])), 4
            )

        # ── Nodes ──
        for i in range(self.num_nodes):
            x, y = int(self.positions[i][0]), int(self.positions[i][1])
            if self.solved:
                # Glow effect
                t = (pygame.time.get_ticks() - self.solve_time) / 500.0
                pulse = int(128 + 127 * math.sin(t * 3 + i * 0.5))
                color = (pulse // 2, pulse, pulse // 2)
            elif i == self.dragging:
                color = NODE_DRAG_COLOR
            else:
                color = NODE_COLOR
            pygame.draw.circle(self.screen, color, (x, y), self.node_radius)
            pygame.draw.circle(self.screen, (255, 255, 255), (x, y), self.node_radius, 1)

        # ── HUD ──
        level_text = self.font.render(
            f"Level {self.level + 1}/{len(LEVELS)}  "
            f"Nodes: {self.num_nodes}  Edges: {len(self.edges)}  "
            f"Crossings: {self.num_crossings}",
            True,
            HUD_COLOR,
        )
        self.screen.blit(level_text, (10, 12))

        help_text = self.small_font.render(
            "Drag nodes to untangle | R: restart | Q: quit", True, (120, 120, 140)
        )
        self.screen.blit(help_text, (WIDTH - help_text.get_width() - 10, HEIGHT - 22))

        # ── Celebration overlay ──
        if self.solved:
            t = (pygame.time.get_ticks() - self.solve_time) / 1000.0
            alpha = int(min(180, 40 + 30 * math.sin(t * 2)))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((30, 200, 80, alpha))
            self.screen.blit(overlay, (0, 0))

            solved_text = self.big_font.render("SOLVED!", True, (255, 255, 255))
            sx = (WIDTH - solved_text.get_width()) // 2
            sy = HEIGHT // 2 - 40
            self.screen.blit(solved_text, (sx, sy))

            if self.level < len(LEVELS) - 1:
                next_text = self.font.render(
                    "Press N for next level", True, (255, 255, 255)
                )
            else:
                next_text = self.font.render(
                    "All levels complete!", True, (255, 255, 255)
                )
            nx = (WIDTH - next_text.get_width()) // 2
            self.screen.blit(next_text, (nx, sy + 60))

        pygame.display.flip()


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Game().run()
