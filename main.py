import fnmatch
import math
import os
import random
import re
import subprocess
import sys

try:
    import pygame
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--user', 'pygame'])
    import pygame

try:
    import pymunk
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--user', 'pymunk'])
    import pymunk
finally:
    from pymunk.vec2d import Vec2d
    import pymunk.pygame_util

# Colors
BRICK_RED = (170, 74, 68, 255)
WHITE = (255, 255, 255, 255)
HALF_WHITE = (255, 255, 255, 128)
LIGHT_GRAY = (211, 211, 211, 255)
GRAY = (128, 128, 128, 255)
DARK_GRAY = (44, 62, 80, 255)
BLACK = (0, 0, 0, 255)
BLUE = (0, 0, 255, 255)
HALF_BLUE = (0, 0, 255, 128)
SCARLET = (187, 0, 0, 255)
GOLD = (255, 215, 0, 255)
GREEN = (50, 205, 50, 255)

# Categories
REDMASK = pymunk.ShapeFilter.ALL_MASKS() ^ 1
BLUEMASK = pymunk.ShapeFilter.ALL_MASKS() ^ 2


def alpha_sort_list(unsorted_list: list) -> list:
    def try_int(symbols):
        try:
            s = float(symbols)
        except ValueError:
            s = symbols
        return s

    unsorted_list.sort(key=lambda s: [try_int(c) for c in re.split(r'[+-]?([0-9]+(?:[.][0-9]*)?|[.][0-9]+)', s)])
    return unsorted_list


def draw_rect_alpha(surface, color, rect):
    shape_surf = pygame.Surface(pygame.Rect(rect).size, pygame.SRCALPHA)
    pygame.draw.rect(shape_surf, color, shape_surf.get_rect())
    surface.blit(shape_surf, rect)


def draw_circle_alpha(surface, color, center, radius):
    target_rect = pygame.Rect(center, (0, 0)).inflate((radius * 2, radius * 2))
    shape_surf = pygame.Surface(target_rect.size, pygame.SRCALPHA)
    pygame.draw.circle(shape_surf, color, (radius, radius), radius)
    surface.blit(shape_surf, target_rect)


def draw_polygon_alpha(surface, color, points):
    lx, ly = zip(*points)
    min_x, min_y, max_x, max_y = min(lx), min(ly), max(lx), max(ly)
    target_rect = pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)
    shape_surf = pygame.Surface(target_rect.size, pygame.SRCALPHA)
    pygame.draw.polygon(shape_surf, color, [(x - min_x, y - min_y) for x, y in points])
    surface.blit(shape_surf, target_rect)


def message(surface: pygame.Surface, msg: str, color: tuple[int, int, int, int] = LIGHT_GRAY,
            collide: bool = False, collide_box: bool = False, collide_keyboard: bool = False,
            point: Vec2d | tuple = Vec2d(0, 0), align='center', font='ComicSansMs', font_size=35) -> pygame.Rect:
    font = pygame.font.SysFont(font, font_size)
    mesg = font.render(msg, True, color)

    try:
        msg_rect = mesg.get_rect(**{align: point})
    except TypeError:
        print(Exception)
        return mesg.get_rect(center=point)

    if collide and msg_rect.collidepoint(pygame.mouse.get_pos()):
        mesg = font.render(msg, True, SCARLET)
    if collide and collide_keyboard:
        mesg = font.render(msg, True, SCARLET)
    if collide_box:
        m_c_x, m_c_y = msg_rect.center
        points = ((m_c_x - 18, m_c_y + 18), (m_c_x - 18, m_c_y - 18),
                  (m_c_x + 18, m_c_y - 18), (m_c_x + 18, m_c_y + 18))
        pygame.draw.lines(surface, WHITE, True, points)
        c_b = pygame.Rect(m_c_x - 17, m_c_y - 17, 35, 35)  # collide box
        if msg_rect.collidepoint(pygame.mouse.get_pos()):
            surface.fill(BRICK_RED, c_b)

    surface.blit(mesg, msg_rect)
    return msg_rect


class Player:
    """init and draw player"""

    def __init__(self, space: pymunk.Space, block_size: int, start_position: pymunk.Vec2d | tuple = Vec2d(0, 0)):
        self.space = space
        self.b0 = self.space.static_body
        self.body = pymunk.Body()
        self.start_position = start_position

        self.player = pymunk.Shape
        self.density = 0.5
        self.friction = 0.999
        self.elasticity = 0.5
        self.radius = block_size / 5

        self.impulse = 0, -150000 * (2 / 5)
        self.velocity = 35

        self.camera = pygame.Vector2((0, 0))
        self.camera_mode = False

        self.motor = pymunk.constraints.SimpleMotor(self.b0, self.body, 0)
        self.space.add(self.motor)

        self.fly = False
        self.inwater = False

    def draw(self):
        self.body.position = self.start_position
        self.player = pymunk.Circle(self.body, self.radius)
        self.player.density = self.density
        self.player.friction = self.friction
        self.player.elasticity = self.elasticity
        self.player.color = SCARLET
        self.space.add(self.body, self.player)
        self.player.filter = pymunk.ShapeFilter(mask=REDMASK)

    def control(self, direction, map_c):
        def j():
            for s in map_c.shapes:
                if len(self.player.shapes_collide(s).points) != 0:
                    return True
            for s in map_c.blue_wall_block:
                if len(self.player.shapes_collide(s).points) != 0:
                    return True
            for s in map_c.red_wall_block:
                if len(self.player.shapes_collide(s).points) != 0:
                    return True
            return False

        def w():
            if self.inwater:
                self.space.gravity = (0, 400)
                return True
            else:
                self.space.gravity = (0, 900)
                return False

        if j():
            if direction == 0:
                """key not pressed"""
                self.motor.rate = 0
            elif direction == 1:
                """pressed right arrow"""
                if w():
                    self.motor.rate = -self.velocity / 2
                else:
                    self.motor.rate = -self.velocity
            elif direction == -1:
                """pressed left arrow"""
                if w():
                    self.motor.rate = self.velocity / 2
                else:
                    self.motor.rate = self.velocity
            if direction == 2:
                """jump"""
                if w():
                    self.body.apply_impulse_at_world_point((self.impulse[0] / 2, self.impulse[1] / 2),
                                                           self.body.position)
                else:
                    self.body.apply_impulse_at_world_point(self.impulse, self.body.position)
                    self.fly = True

        elif self.fly:
            self.motor.rate = -self.motor.rate / 2
            self.fly = False
        else:
            if direction == 1:
                """pressed right arrow"""
                self.body.apply_impulse_at_world_point((self.velocity * 25, 0), self.body.position)
            elif direction == -1:
                """pressed left arrow"""
                self.body.apply_impulse_at_world_point((-self.velocity * 25, 0), self.body.position)
            elif direction == 2 and w():
                self.body.apply_impulse_at_world_point((self.impulse[0] / 2, self.impulse[1] / 2),
                                                       self.body.position)

    def camera_moving(self, surface: pygame.Surface, camera_layer: pygame.Surface):
        """the camera following player"""
        if self.camera_mode:
            pressed = pygame.key.get_pressed()
            camera_move = pygame.Vector2()
            if pressed[pygame.K_w]: camera_move += (0, 1)
            if pressed[pygame.K_a]: camera_move += (1, 0)
            if pressed[pygame.K_s]: camera_move += (0, -1)
            if pressed[pygame.K_d]: camera_move += (-1, 0)
            if camera_move.length() > 0: camera_move.normalize_ip()
            self.camera += camera_move * (self.radius / 3)
        else:
            self.camera = (-self.body.position[0] + App.w / 2, -self.body.position[1] + App.h / 2)
        surface.blit(camera_layer, self.camera)


class Map:
    map = []
    shapes = []
    wall_rects = []

    def __init__(self, space: pymunk.Space, player: Player, surface: pygame.Surface, block_size=75):
        self.block_size = block_size
        self.l_x = 0
        self.l_y = 0
        self.size = (0, 0)

        self.level_score = 0
        self.bonus_list = []

        self.exit_point = (0, 0)
        self.exit_shape = pymunk.Shape

        self.spikes_points = []
        self.spikes_shapes = []

        self.check_points_list = []

        self.space = space
        self.b0 = space.static_body
        self.map_number = 0
        self.map_list = []
        self.load_map_list()
        self.map_rect = pygame.Rect(0, 0, 0, 0)
        self.player = player
        self.player_rect = pygame.Rect(0, 0, 0, 0)
        self.check_point = (0, 0)
        self.current_map = ''

        self.boxes = []

        self.water = []

        self.blue_wall = []
        self.blue_wall_block = []
        self.blue_marker = []

        self.red_wall = []
        self.red_wall_block = []
        self.red_marker = []

    def load_map_list(self):
        file_list = os.listdir('./maps/')
        pattern = 'map_*.bin'
        for entry in file_list:
            if fnmatch.fnmatch(entry, pattern):
                self.map_list.append(entry)
        self.map_list = alpha_sort_list(self.map_list)

    def clear(self):
        for i in self.space.shapes:
            self.space.remove(i)
        for i in self.space.bodies:
            self.space.remove(i)

        self.exit_shape = pymunk.Shape

        self.spikes_points = []
        self.spikes_shapes = []
        self.boxes = []
        self.blue_marker = []
        self.bonus_list = []
        self.blue_wall = []
        self.blue_wall_block = []
        self.red_wall_block = []
        self.red_marker = []
        self.red_wall = []
        self.water = []
        self.wall_rects = []

        self.level_score = 0

        Map.map = []
        Map.shapes = []

    def load_map(self, file):
        self.clear()
        map_file = open(f"./maps/{file}", mode='r', encoding='utf-8')
        m = ''
        for line in map_file.readlines():
            m += line
        map_file.close()
        Map.map = m.split()

    def wall_sample_func(self, point: tuple) -> bool:
        """
        отрисовка блоков по символьной карте
        # — стена
        . — пространство
        @ — старт
        $ — бонус
        s — сохранение
        w — шипы
        c — финиш
        - — стена без коллизии
        b — синий маркер
        B — синяя стена
        r — красный маркер
        R — красная стена
        ~ — вода
        """
        x = int(point[0])
        y = int(point[1])
        if Map.map[y][x] == '@':
            self.player.start_position = (x * self.block_size + self.block_size / 2,
                                          y * self.block_size + self.block_size / 2)
            self.check_point = (x * self.block_size + self.block_size / 2,
                                y * self.block_size + self.block_size / 2)
            self.player.draw()
        if Map.map[y][x] == 'c':
            self.exit_point = (x * self.block_size, y * self.block_size)
        if Map.map[y][x] == 'w':
            self.spikes_points.append((x * self.block_size, y * self.block_size))
        if Map.map[y][x] == 's':
            self.check_points_list.append((x * self.block_size + self.block_size / 2,
                                           y * self.block_size + self.block_size - 15))
        if Map.map[y][x] == '$':
            self.bonus_list.append((x * self.block_size + self.block_size / 2,
                                    y * self.block_size + self.block_size - 15))
        if Map.map[y][x] == '-':
            self.boxes.append((x * self.block_size, y * self.block_size))
        if Map.map[y][x] == 'b':
            self.blue_marker.append((x * self.block_size + self.block_size / 2,
                                     y * self.block_size + self.block_size - 15))
        if Map.map[y][x] == 'B':
            self.blue_wall.append((x * self.block_size, y * self.block_size))
        if Map.map[y][x] == 'r':
            self.red_marker.append((x * self.block_size + self.block_size / 2,
                                    y * self.block_size + self.block_size - 15))
        if Map.map[y][x] == 'R':
            self.red_wall.append((x * self.block_size, y * self.block_size))
        if Map.map[y][x] == '~':
            self.water.append((x * self.block_size, y * self.block_size))
        return True if Map.map[y][x] == '#' else False

    def draw_map(self):
        """init map's shapes"""
        self.l_x = len(Map.map[0])
        self.l_y = len(Map.map)
        self.size = self.l_x * self.block_size, self.l_y * self.block_size
        for i in range(self.l_x):
            for j in range(self.l_y):
                if self.wall_sample_func(point=(i, j)):
                    x = i * self.block_size
                    y = j * self.block_size
                    self.wall_rects.append(pygame.Rect(x, y, self.block_size, self.block_size))

        v1, v2 = self.exit_point
        vertices = (
            (v1 + 5, v2 + self.block_size), (v1 + 10, v2 + self.block_size / 3),
            (v1 + self.block_size / 2, v2 + self.block_size / 5),
            (v1 + self.block_size - 10, v2 + self.block_size / 3), (v1 + self.block_size - 5, v2 + self.block_size)
        )
        self.exit_shape = pymunk.Poly(self.b0, vertices, radius=0)
        self.exit_shape.color = (random.randrange(0, 200, 4), random.randrange(0, 200, 4),
                                 random.randrange(24, 255, 8), 255)
        self.exit_shape.density = 0.9999
        self.exit_shape.friction = 0.1
        self.exit_shape.elasticity = 0.1
        self.space.add(self.exit_shape)

        for s in self.spikes_points:
            x, y = s
            vertices = (
                (x, y + self.block_size),
                (x + self.block_size / 2, y + self.block_size / 3),
                (x + self.block_size, y + self.block_size),
            )
            shape = pymunk.Poly(self.b0, vertices, radius=1)
            shape.color = GRAY
            shape.density = 0.9999
            self.spikes_shapes.append(shape)
            self.space.add(shape)

        self.color_wall_draw()

    def draw_map_cycle(self, surface: pygame.Surface):
        shapes = self.shapes
        for w in self.wall_rects:
            pygame.draw.rect(surface, BRICK_RED, w)
            pygame.draw.rect(surface, DARK_GRAY, w, 2)
            if self.player_rect.colliderect(w):
                if len(shapes) != 0:
                    f = True
                    for s in shapes:
                        if s.point_query(w.center).distance < 25:
                            f = False
                    if f:
                        vertices = (w.topleft, w.topright,
                                    w.bottomleft, w.bottomright)
                        shape = pymunk.Poly(self.b0, vertices, radius=0)
                        shape.color = BRICK_RED
                        shape.friction = 0.999
                        shape.elasticity = 0.5
                        self.space.add(shape)
                        self.shapes.append(shape)
                else:
                    vertices = (w.topleft, w.topright,
                                w.bottomleft, w.bottomright)
                    shape = pymunk.Poly(self.b0, vertices, radius=0)
                    shape.color = BRICK_RED
                    shape.friction = 0.999
                    shape.elasticity = 0.5
                    self.space.add(shape)
                    self.shapes.append(shape)
            else:
                for s in shapes:
                    if s.point_query(w.center).distance < 25:
                        self.shapes.remove(s)
                        self.space.remove(s)

    def map_end(self) -> bool:
        return True if len(self.player.player.shapes_collide(self.exit_shape).points) != 0 else False

    def spikes_collide(self) -> bool:
        for s in self.spikes_shapes:
            if len(self.player.player.shapes_collide(s).points) != 0:
                return True
        return False

    def checkpoint(self):
        for c in self.check_points_list:
            if self.player.player.point_query(c).distance < 20:
                self.check_point = c
                print('\ncheckpoint')

    def bonus_draw(self, surface: pygame.Surface):
        for b in self.bonus_list:
            pygame.draw.circle(surface, GOLD, b, 5)

    def bonus_keep(self):
        for b in self.bonus_list:
            if self.player.player.point_query(b).distance < 1:
                self.level_score += 1
                self.bonus_list.remove(b)

    def box_draw(self, surface: pygame.Surface):
        for b in self.boxes:
            rect = pygame.Rect(b[0], b[1], self.block_size, self.block_size)
            pygame.draw.rect(surface, BRICK_RED, rect)
            pygame.draw.rect(surface, DARK_GRAY, rect, 2)
        for s in Map.shapes:
            vertices = s.get_vertices()[0]
            rect = pygame.Rect(vertices[0], vertices[1], self.block_size, self.block_size)
            pygame.draw.rect(surface, DARK_GRAY, rect, 2)

    def water_draw(self, surface: pygame.Surface):
        for w in self.water:
            rect = pygame.Rect(w[0], w[1], self.block_size, self.block_size)
            draw_rect_alpha(surface, HALF_BLUE, rect)

    def marker_draw(self, surface: pygame.Surface):
        for m in self.blue_marker:
            pygame.draw.circle(surface, BLUE, m, self.player.radius)
        for m in self.red_marker:
            pygame.draw.circle(surface, SCARLET, m, self.player.radius)

    def marker_collide(self):
        for m in self.blue_marker:
            if self.player.player.point_query(m).distance < 1:
                self.blue_marker.remove(m)
                self.player.player.color = BLUE
                self.player.player.filter = pymunk.ShapeFilter(mask=BLUEMASK)

        for m in self.red_marker:
            if self.player.player.point_query(m).distance < 1:
                self.red_marker.remove(m)
                self.player.player.color = SCARLET
                self.player.player.filter = pymunk.ShapeFilter(mask=REDMASK)

    def color_wall_draw(self):
        for w in self.blue_wall:
            x, y = w[0], w[1]
            b = self.block_size
            vertices = ((x, y), (x + b, y),
                        (x, y + b), (x + b, y + b))
            rs = pymunk.Poly(self.b0, vertices)
            rs.friction = 0.1
            rs.elasticity = 0.1
            rs.color = BLUE
            rs.filter = pymunk.ShapeFilter(categories=2)
            self.space.add(rs)
            self.blue_wall_block.append(rs)
        for w in self.red_wall:
            x, y = w[0], w[1]
            b = self.block_size
            vertices = ((x, y), (x + b, y),
                        (x, y + b), (x + b, y + b))
            rs = pymunk.Poly(self.b0, vertices)
            rs.friction = 0.1
            rs.elasticity = 0.1
            rs.color = SCARLET
            rs.filter = pymunk.ShapeFilter(categories=1)
            self.space.add(rs)
            self.red_wall_block.append(rs)

    def water_collide(self):
        p = self.player.body.position
        for w in self.water:
            rect_w = pygame.Rect(w[0], w[1], self.block_size, self.block_size)
            rect_p = pygame.Rect(p[0]-self.player.radius, p[1]-self.player.radius,
                                 self.player.radius*2, self.player.radius*2)
            if rect_p.colliderect(rect_w):
                self.player.inwater = True
                return
            else:
                self.player.inwater = False

    def pri(self):
        """print service info by F5"""
        print('\n')
        print(f'now draw {len(self.shapes)} shapes')
        print(f'first block coords: {self.shapes[0].body.position}')
        print(f'distance to first block: {self.player.player.point_query(self.shapes[0].body.position).distance}')
        """оптимальная дистанция рисования 650 пикселов"""


class App:
    screen_size = w, h = (800, 600)
    caption = 'BounceBall Q'

    def __init__(self):
        """Initializing pygame, pymunk set main variables"""
        pygame.init()
        pygame.display.set_caption(self.caption)
        self.surface = pygame.display.set_mode(App.screen_size, pygame.DOUBLEBUF, 32, vsync=True)
        self.camera_layer = pygame.Surface((4000, 4000), pygame.DOUBLEBUF)
        self.draw_option = pymunk.pygame_util.DrawOptions(self.camera_layer)
        self.space = pymunk.Space()

        self.block_size = 50

        self.player = Player(self.space, block_size=self.block_size)

        self.map = Map(self.space, self.player, self.surface, self.block_size)
        self.map.current_map = self.map.map_list[0]
        self.map.load_map(self.map.map_list[0])

        self.space.gravity = (0, 900)
        self.fps = 24
        self.fps_counter = False
        self.clock = pygame.time.Clock()

        self.init_draw()
        self.running = False
        self.main_menu_run = True
        self.pause = False

        self.r = 0  # counter of physic's engine step before frame tick
        self.space_step = 3  # number calc of physic per frame

        self.shortcuts = {
            pygame.K_F1: 'self.fps_counter = True if not self.fps_counter else False; '
                         'pygame.display.set_caption(App.caption)',
            pygame.K_ESCAPE: 'self.running = False; self.pause = True; self.main_menu_run = True',
            pygame.K_F2: 'self.endgame_screen()',
            pygame.K_c: 'self.player.camera_mode = True if not self.player.camera_mode else False',
            pygame.K_F5: 'self.map.pri()'
        }  # keyboard's shortcut

        self.direction = {
            'LEFT': -1,
            'STOP': 0,
            'RIGHT': 1,
            'JUMP': 2,
        }

    def main_menu(self):
        box_number = -1
        while self.main_menu_run:
            self.surface.fill(BLACK)
            message(self.surface, f'Текущая карта: {self.map.current_map}',
                    color=BRICK_RED, point=Vec2d(0, 0), align=('topleft'), font_size=24)
            message(self.surface, f'{self.caption}', color=BRICK_RED, point=(self.w / 2, self.h / 3))
            game_start = message(self.surface, 'продолжить' if self.pause else 'начать игру',
                                 point=(self.w / 2, self.h / 2), collide=True,
                                 collide_keyboard=True if box_number == 0 else False)
            map_select = message(self.surface, 'выбрать карту', point=(self.w / 2, self.h / 2 + 50),
                                 collide=True, collide_keyboard=True if box_number == 1 else False)
            if self.pause:
                restart = message(self.surface, 'перезапустить уровень', point=(self.w / 2, self.h / 2 + 100),
                                  collide=True, collide_keyboard=True if box_number == 2 else False)
                pass
            exit_game = message(self.surface, 'выйти из игры',
                                point=(self.w / 2, self.h / 2 + (150 if self.pause else 100)),
                                collide=True,
                                collide_keyboard=True if box_number == (3 if self.pause else 2) else False)

            mp = pygame.mouse.get_pos()
            if (game_start.collidepoint(mp) or
                    map_select.collidepoint(mp) or
                    exit_game.collidepoint(mp)):
                box_number = -1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.main_menu_run = False
                    self.running = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if game_start.collidepoint(event.pos):
                        self.running = True
                        self.pause = False
                        self.run()
                    elif map_select.collidepoint(event.pos):
                        self.map_selection()
                    elif exit_game.collidepoint(event.pos):
                        self.main_menu_run = False
                        self.running = False
                    elif self.pause and restart.collidepoint(event.pos):
                        self.map.load_map(self.map.current_map)
                        self.map.draw_map()
                        self.pause = False
                        self.running = True
                        self.run()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if box_number == 0 or box_number == -1:
                            self.running = True
                            self.pause = False
                            if not self.pause: self.run()
                        elif box_number == 1:
                            self.map_selection()
                        elif self.pause and box_number == 2:
                            self.map.load_map(self.map.current_map)
                            self.map.draw_map()
                            self.pause = False
                            self.running = True
                            self.run()
                        elif box_number == (3 if self.pause else 2):
                            self.main_menu_run = False
                            self.running = False
                    if event.key == pygame.K_UP:
                        if box_number == -1:
                            box_number = 3 if self.pause else 2
                        elif box_number == 0:
                            pass
                        else:
                            box_number -= 1
                    if event.key == pygame.K_DOWN:
                        if box_number == -1:
                            box_number = 0
                        elif box_number == (3 if self.pause else 2):
                            pass
                        else:
                            box_number += 1

            pygame.display.flip()
            pass

    def map_selection(self):
        """selecting of map"""
        m_s = True
        page = 0
        box_number = -1

        self.map.map_list = []
        self.map.load_map_list()

        while m_s:
            self.surface.fill(BLACK)
            message(self.surface, f'Текущая карта: {self.map.current_map}',
                    color=BRICK_RED, point=Vec2d(0, 0), align='topleft', font_size=24)
            message(self.surface, 'Bounce Ball Rare', color=BRICK_RED, point=(self.w / 2, self.h / 3))
            y = 0  # number of map on page
            count_of_page = math.ceil(len(self.map.map_list) / 4)
            map_rect_list = []
            page_rect_list = []
            try:
                if len(self.map.map_list) <= 5:
                    for m in self.map.map_list:
                        map_rect_list.append(message(self.surface, m, color=LIGHT_GRAY,
                                                     point=(self.w / 2, self.h / 2 + y * 50),
                                                     collide=True, collide_keyboard=True if box_number == y else False))
                        y += 1
                else:
                    for i in range(count_of_page):
                        page_rect_list.append(message(self.surface, str(i + 1), color=WHITE,
                                                      point=(
                                                          (self.w / 2 - count_of_page / 2 * 50 + 25) + i * 60,
                                                          self.h - 50),
                                                      collide_box=True))
                    p = page * 4
                    if 4 + p > len(self.map.map_list):
                        for m in range(0, abs(len(self.map.map_list) - 4 * (count_of_page - 1))):
                            map_rect_list.append(message(self.surface, self.map.map_list[m + p], color=LIGHT_GRAY,
                                                         point=(self.w / 2, self.h / 2 + m * 50),
                                                         collide=True,
                                                         collide_keyboard=True if box_number == m else False))
                    else:
                        for m in range(0, 4):
                            map_rect_list.append(message(self.surface, self.map.map_list[m + p], color=LIGHT_GRAY,
                                                         point=(self.w / 2, self.h / 2 + m * 50),
                                                         collide=True,
                                                         collide_keyboard=True if box_number == m else False))
            except IndexError as e:
                print(e)

            for m in map_rect_list:
                if m.collidepoint(pygame.mouse.get_pos()):
                    box_number = -1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    m_s = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        m_s = False
                    if event.key == pygame.K_UP:
                        if box_number == -1:
                            box_number = map_rect_list.index(map_rect_list[-1])
                        elif box_number == 0:
                            pass
                        else:
                            box_number -= 1
                    if event.key == pygame.K_DOWN:
                        if box_number == -1:
                            box_number = 0
                        elif box_number == map_rect_list.index(map_rect_list[-1]):
                            pass
                        else:
                            box_number += 1
                    if event.key == pygame.K_RETURN and box_number != -1:
                        self.map.current_map = self.map.map_list[map_rect_list.index(map_rect_list[box_number])]
                        self.map.load_map(self.map.map_list[map_rect_list.index(map_rect_list[box_number])])
                        self.map.draw_map()
                        self.camera_layer = pygame.Surface(self.map.size, pygame.DOUBLEBUF)

                        self.camera_layer = pygame.Surface(self.map.size)
                        self.draw_option = pymunk.pygame_util.DrawOptions(self.camera_layer)
                        m_s = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for r in map_rect_list:
                        if r.collidepoint(event.pos):
                            self.map.current_map = self.map.map_list[map_rect_list.index(r) + 4 * page]
                            self.map.load_map(self.map.map_list[map_rect_list.index(r) + 4 * page])
                            self.map.draw_map()
                            self.camera_layer = pygame.Surface(self.map.size, pygame.DOUBLEBUF)

                            self.camera_layer = pygame.Surface(self.map.size)
                            self.draw_option = pymunk.pygame_util.DrawOptions(self.camera_layer)
                            m_s = False
                    if count_of_page > 1:
                        for pr in page_rect_list:
                            if pr.collidepoint(event.pos):
                                page = page_rect_list.index(pr)
            pygame.display.flip()
            map_rect_list.clear()
        pass

    def run(self):
        """Run game-loop"""
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.main_menu_run = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.player.control(self.direction['JUMP'], self.map)
                    else:
                        self.do_events(event)

            key = pygame.key.get_pressed()
            if key[pygame.K_LEFT]:
                self.player.control(self.direction['LEFT'], self.map)
            elif key[pygame.K_RIGHT]:
                self.player.control(self.direction['RIGHT'], self.map)
            else:
                self.player.control(self.direction['STOP'], self.map)

            if self.fps_counter:
                pygame.display.set_caption(f'{App.caption}, FPS = {str(self.clock.get_fps())}')

            self.draw()
            self.space.step(1 / self.space_step / self.fps)
            if self.r == self.space_step:
                self.clock.tick(self.fps)
                self.r = 0
            else:
                self.r += 1

            if self.map.spikes_collide():
                self.death()

            self.map.checkpoint()

            if self.map.map_end():
                self.running = False
                self.endgame_screen()

    def death(self):
        self.player.body.position = self.map.check_point

    def endgame_screen(self):
        endgame = True
        msg_boxes = []
        box_number = -1
        while endgame:
            self.surface.fill(BLACK)
            message(self.surface, f'Уровень {self.map.current_map} завершён!', BRICK_RED,
                    point=(self.w / 2, self.h / 3))
            if self.map.map_list[-1] == self.map.current_map:
                message(self.surface, 'Вы прошли игру! Ура=)', SCARLET, point=(self.w / 2, self.h / 3 + 50))
                msg_boxes.append('END')
            else:
                msg_boxes.append(message(self.surface, 'продолжить', LIGHT_GRAY,
                                         point=(self.w / 2, self.h / 2 + 0 * 50), collide=True,
                                         collide_keyboard=True if box_number == 0 else False))
            msg_boxes.append(message(self.surface, 'выбрать карту', LIGHT_GRAY,
                                     point=(self.w / 2, self.h / 2 + 1 * 50), collide=True,
                                     collide_keyboard=True if box_number == 1 else False))
            msg_boxes.append(message(self.surface, 'выйти', LIGHT_GRAY,
                                     point=(self.w / 2, self.h / 2 + 2 * 50), collide=True,
                                     collide_keyboard=True if box_number == 2 else False))

            for b in msg_boxes:
                if b != 'END':
                    if b.collidepoint(pygame.mouse.get_pos()):
                        box_number = -1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    endgame = False
                    self.main_menu_run = False
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if msg_boxes[0] != 'END' and (box_number == -1 or box_number == 0):
                            self.map.current_map = self.map.map_list[self.map.map_list.index(self.map.current_map) + 1]
                            self.map.load_map(self.map.current_map)
                            self.map.draw_map()
                            self.camera_layer = pygame.Surface(self.map.size, pygame.DOUBLEBUF)

                            self.camera_layer = pygame.Surface(self.map.size)
                            self.draw_option = pymunk.pygame_util.DrawOptions(self.camera_layer)

                            endgame = False
                            self.main_menu_run = False
                            self.running = True
                        if box_number == 1:
                            endgame = False
                            self.main_menu_run = False
                            self.map_selection()
                            self.running = True
                        if box_number == 2:
                            endgame = False
                            self.main_menu_run = True
                            self.running = False
                    if event.key == pygame.K_UP:
                        if box_number == -1:
                            box_number = msg_boxes.index(msg_boxes[-1])
                        elif box_number == 1 if self.map.map_list[-1] == self.map.current_map else 0:
                            pass
                        else:
                            box_number -= 1
                    if event.key == pygame.K_DOWN:
                        if box_number == -1:
                            box_number = 1 if self.map.map_list[-1] == self.map.current_map else 0
                        elif box_number == msg_boxes.index(msg_boxes[-1]):
                            pass
                        else:
                            box_number += 1
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if msg_boxes[0] != 'END' and msg_boxes[0].collidepoint(event.pos):
                        self.map.current_map = self.map.map_list[self.map.map_list.index(self.map.current_map) + 1]
                        self.map.load_map(self.map.current_map)
                        self.map.draw_map()
                        self.camera_layer = pygame.Surface(self.map.size, pygame.DOUBLEBUF)

                        self.camera_layer = pygame.Surface(self.map.size)
                        self.draw_option = pymunk.pygame_util.DrawOptions(self.camera_layer)

                        endgame = False
                        self.main_menu_run = False
                        self.running = True
                    if msg_boxes[1].collidepoint(event.pos):
                        endgame = False
                        self.main_menu_run = False
                        self.map_selection()
                        self.running = True
                    if msg_boxes[2].collidepoint(event.pos):
                        endgame = False
                        self.main_menu_run = True
                        self.running = False

            pygame.display.flip()

    def do_events(self, event):
        """Handling keyboard events"""
        k = event.key
        cmd = ''
        if k in self.shortcuts:
            cmd = self.shortcuts[k]
        if cmd != '':
            try:
                exec(cmd)
            except Exception as e:
                print(f'cmd error: <{cmd}> with exception <{e}>')

    def draw(self):
        self.surface.fill(BLACK)
        self.camera_layer.fill(BLACK)
        self.space.debug_draw(self.draw_option)

        self.map.bonus_draw(self.camera_layer)
        self.map.bonus_keep()
        self.map.marker_collide()
        self.map.box_draw(self.camera_layer)
        self.map.marker_draw(self.camera_layer)
        self.map.water_draw(self.camera_layer)
        self.map.water_collide()

        p_x, p_y = self.player.body.position
        self.map.player_rect = pygame.Rect(p_x - self.block_size, p_y - self.block_size,
                                           self.block_size * 2, self.block_size * 2)
        self.map.draw_map_cycle(self.camera_layer)

        self.player.camera_moving(self.surface, self.camera_layer)

        rect = pygame.Rect(0, 0, self.w, 50)
        draw_rect_alpha(self.surface, HALF_WHITE, rect)
        rb = message(self.surface, f'LEVEL {self.map.map_list.index(self.map.current_map)}|',
                     color=GREEN, point=(5, 0), align='topleft')
        rb = message(self.surface, f'SCORE {self.map.level_score}|', GREEN, point=(rb.right, 0), align='topleft')
        # print(f'surface rect = {self.surface.get_rect()}')
        # print(f'camera rect = {self.camera_layer.get_rect()}')
        # print(f'first shape = {Map.shapes[0].get_vertices()}')

        pygame.display.flip()

    def init_draw(self):
        self.surface.fill(BLACK)
        self.map.draw_map()
        self.camera_layer = pygame.Surface(self.map.size, pygame.DOUBLEBUF)
        self.player.rect = pygame.Rect(self.map.exit_point[0], self.map.exit_point[1],
                                       self.map.block_size, self.map.block_size)
        self.draw_option = pymunk.pygame_util.DrawOptions(self.camera_layer)
        self.space.debug_draw(self.draw_option)

        p_x, p_y = self.player.body.position
        self.map.player_rect = pygame.Rect(p_x - self.block_size, p_y - self.block_size,
                                           self.block_size * 2, self.block_size * 2)
        self.map.draw_map_cycle(self.camera_layer)

        pygame.display.flip()

    def __del__(self):
        pygame.quit()


if __name__ == '__main__':
    # pymunk.pygame_util.positive_y_is_up = True
    App().main_menu()
