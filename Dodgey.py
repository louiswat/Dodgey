#!/usr/bin/env python3.10
# Created by Louis Watrelos

import random

import pygame
import pygame.joystick
from pygame import Color, joystick
from pygame.image import load
from pygame.math import Vector2
from pygame.mixer import Sound
from pygame.transform import rotozoom

SCREEN_W = 1680
SCREEN_H = 1050
SpaceshipUp = Vector2(0, -1)


def get_random_position(surface):
    return Vector2(random.randrange(surface.get_width()),random.randrange(surface.get_height()),)


def get_random_velocity(min_speed, max_speed):
    speed = random.randint(min_speed, max_speed)
    angle = random.randrange(0, 360)
    return Vector2(speed, 0).rotate(angle)


def load_sound(name):
    path = f"./Assets/Sound/{name}.wav"
    return Sound(path)


def load_sprite(name, with_alpha=True):
    path = f"Assets/Sprites/{name}.png"
    loaded_sprite = load(path)
    if with_alpha:
        return loaded_sprite.convert_alpha()
    else:
        return loaded_sprite.convert()


def print_text(surface, position, text, font, color=Color("tomato")):
    text_surface = font.render(text, True, color)

    rect = text_surface.get_rect()
    rect.center = position

    surface.blit(text_surface, rect)

def wrap_position(position, surface):
    x, y = position
    w, h = surface.get_size()
    return Vector2(x % w, y % h)


class GameObject:
    def __init__(self, position, sprite, velocity):
        self.position = Vector2(position)
        self.sprite = sprite
        self.radius = sprite.get_width() / 2
        self.velocity = Vector2(velocity)

    def draw(self, surface):
        blit_position = self.position - Vector2(self.radius)
        surface.blit(self.sprite, blit_position)

    def move(self, surface):
        self.position = wrap_position(self.position + self.velocity, surface)

    def collides_with(self, other_obj):
        distance = self.position.distance_to(other_obj.position)
        return distance < self.radius + other_obj.radius


class Asteroid(GameObject):
    def __init__(self, position, create_asteroid_callback, size=3):
        self.create_asteroid_callback = create_asteroid_callback
        self.size = size

        size_to_scale = {
            3: 1,
            2: 0.5,
            1: 0.25,
        }
        scale = size_to_scale[size]
        sprite = rotozoom(load_sprite("Asteroid"), 0, scale)

        super().__init__(position, sprite, get_random_velocity(1, 3))

    def split(self):
        if self.size > 1:
            for _ in range(2):
                asteroid = Asteroid(
                    self.position, self.create_asteroid_callback, self.size - 1
                )
                self.create_asteroid_callback(asteroid)


class Bullet(GameObject):
    def __init__(self, position, velocity):
        super().__init__(position, load_sprite("bullet"), velocity)

    def move(self, surface):
        self.position = self.position + self.velocity


class Spaceship(GameObject):
    MANEUVERABILITY = 5
    ACCELERATION = 0.15
    BULLET_SPEED = 3

    def __init__(self, position, create_bullet_callback):
        self.create_bullet_callback = create_bullet_callback

        self.explosion = load_sound("explosion")
        self.laser_sound = load_sound("laser")
        self.direction = Vector2(SpaceshipUp)
        super().__init__(position, load_sprite("Spaceship"), Vector2(0))

    def rotate(self, clockwise=True):
        sign = 1 if clockwise else -1
        angle = self.MANEUVERABILITY * sign
        self.direction.rotate_ip(angle)

    def accelerate(self):
        self.velocity += self.direction * self.ACCELERATION

    def draw(self, surface):
        angle = self.direction.angle_to(SpaceshipUp)
        rotated_surface = rotozoom(self.sprite, angle, 1.0)
        rotated_surface_size = Vector2(rotated_surface.get_size())
        blit_position = self.position - rotated_surface_size * 0.5
        surface.blit(rotated_surface, blit_position)

    def shoot(self):
        bullet_velocity = self.direction * self.BULLET_SPEED + self.velocity
        bullet = Bullet(self.position, bullet_velocity)
        self.create_bullet_callback(bullet)
        self.laser_sound.play()

class Dodgey:
    MIN_DISTANCE = 300

    def __init__(self):
        self._init_pygame()
        self.screen = pygame.display.set_mode((1680, 1050))
        self.background = load_sprite("Back", False)
        self.clock = pygame.time.Clock()
        self.score = 0
        self.font = pygame.font.Font(None, 64)
        self.message = ""

        self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        # self.buttons = self.joysticks[0].get_numbuttons()
        self.end = 0
        self.bullets = []
        self.asteroids = []
        self.spaceship = Spaceship((SCREEN_W/2, SCREEN_H/2), self.bullets.append)

        for _ in range(6):
            while True:
                position = get_random_position(self.screen)
                if position.distance_to(self.spaceship.position) > self.MIN_DISTANCE:
                    break
            self.asteroids.append(Asteroid(position, self.asteroids.append))

    def main_loop(self):
        while True:
            if self._menu():
                break
            self._draw_menu()
        while True:
            self._handle_input()
            self._process_game_logic()
            self._draw()
            if not self.spaceship:
                self.end += 1
                if self.end == 200:
                    self._stop()

    def _menu(self):
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                return True
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self._stop()
            elif self.spaceship and event.type == pygame.KEYDOWN:
                return True
        return False

    def _init_pygame(self):
        pygame.init()
        pygame.joystick.init()
        pygame.display.set_caption("Dodgey")

    def _handle_input(self):
        self.axes = joystick.Joystick(0).get_numaxes()
        for i in range(self.axes):
            if self.spaceship:
                self.axis = self.joysticks[0].get_axis(i)
                if self.axis > 0.5 and i == 0:
                    self.spaceship.rotate(clockwise=True)
                if self.axis < -0.5 and i == 1:
                    self.spaceship.accelerate()
                if self.axis < -0.5 and i == 0:
                    self.spaceship.rotate(clockwise=False)
        for event in pygame.event.get():
            if self.spaceship:
                if event.type == pygame.JOYBUTTONDOWN:
                    self.spaceship.shoot()
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self._stop()
            elif self.spaceship and event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.spaceship.shoot()
        key_pressed = pygame.key.get_pressed()
        if self.spaceship:
            if key_pressed[pygame.K_RIGHT]:
                self.spaceship.rotate(clockwise=True)
            if key_pressed[pygame.K_LEFT]:
                self.spaceship.rotate(clockwise=False)
            if key_pressed[pygame.K_UP]:
                self.spaceship.accelerate()

    def _process_game_logic(self):
        for game_object in self._get_game_objects():
            game_object.move(self.screen)
        if self.spaceship:
            for asteroid in self.asteroids:
                if asteroid.collides_with(self.spaceship):
                    self.message = "You died, game will close shortly"
                    self.spaceship.explosion.play()
                    self.spaceship = None
                    break
        for bullet in self.bullets[:]:
            for asteroid in self.asteroids[:]:
                if asteroid.collides_with(bullet):
                    self.asteroids.remove(asteroid)
                    self.bullets.remove(bullet)
                    asteroid.split()
                    self.score += 100
                    break
        for bullet in self.bullets[:]:
            if not self.screen.get_rect().collidepoint(bullet.position):
                self.bullets.remove(bullet)
        if self.asteroids.__len__() < 10:
            for _ in range(4):
                while True:
                    position = get_random_position(self.screen)
                    if position.distance_to(self.spaceship.position) > self.MIN_DISTANCE:
                        break
                self.asteroids.append(Asteroid(position, self.asteroids.append))

    def _draw(self):
        self.screen.blit(self.background, (0, 0))
        for game_object in self._get_game_objects():
            game_object.draw(self.screen)
        print_text(self.screen, Vector2(SCREEN_W/2, 20), f"Score: {self.score}", self.font)
        pygame.display.flip()
        self.clock.tick(60)

    def _draw_menu(self):
        self.screen.blit(self.background, (0, 0))
        print_text(self.screen, Vector2(SCREEN_W/2, 100), "Dodgey", self.font, Color("Purple"))
        print_text(self.screen, Vector2(self.screen.get_size()) / 2, "Press any button to start.", self.font)
        print_text(self.screen, Vector2(SCREEN_W/2, SCREEN_H-70), "Shoot = buttons   Move = joystick.", self.font, Color("Blue"))
        pygame.display.flip()
        self.clock.tick(60)

    def _get_game_objects(self):
        game_objects = [*self.asteroids, *self.bullets]
        if self.spaceship:
            game_objects.append(self.spaceship)
        return game_objects

    def _stop(self):
        print(self.score)
        quit()



def main():
    dodgey = Dodgey()
    return dodgey.main_loop()


exit(main())
