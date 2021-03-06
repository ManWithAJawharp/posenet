#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun  4 12:57:52 2017

@author: abe
"""

import pygame as pg
import numpy as np

from actor import Actor, AnimatedActor
from text import Line
import game_manager as game
import detect
import util
from event import Event

class Cursor(Actor):
    def __init__(self):
        super(Cursor, self).__init__((100,100))
        
        self.set_image(game.get_image('cursor_standard'))
        
        self.velocity =  np.array((0,0))
        
        game.cursor_down.subscribe(self.cursor_down)
        game.cursor_up.subscribe(self.cursor_up)
        
        self.load_icon = AnimatedActor((64,96), mode='one_shot')
        self.load_icon.set_animation(game.get_animation('load'), (64,64), 20)
        self.load_icon_rect = self.load_icon.surface.get_rect()
        
        self.is_down = False
        self.button_type = None
        
    def __del__(self):
        game.cursor_down.unsubscribe(self.cursor_down)
        game.cursor_up.unsubscribe(self.cursor_up)
        
    def update(self, delta):
        super(Cursor, self).update(delta)
        
        if self.is_down:
            self.load_icon.update(delta)
        
        target = detect.detector.get_current_position()
        force = 10 * util.normalize(target - self.position)
        
        distance_modifier = np.min([100, util.distance(self.position, target)]) / 100
        self.velocity = distance_modifier * (force + 0.9 * self.velocity)
        
        self.position += self.velocity
        
        if self.position[0] < 0:
            self.position[0] = 0
        elif self.position[0] > game.get_screen_size()[0]:
            self.position[0] = game.get_screen_size()[0]
            
        if self.position[1] < 0:
            self.position[1] = 0
        elif self.position[1] > game.get_screen_size()[1]:
            self.position[1] = game.get_screen_size()[1]
        
        game.set_cursor_position(self.position)
    
    def draw(self, surface):
        if not self.is_active: return
        
        if self.is_down and self.button_type is HandScreen: return
        
        self.rect.center = self.position
        self.load_icon.center = self.position
        
        self.surface.fill(pg.Color(0,0,0,0))
        self.surface.blit(self.image, self.image_rect)
        
        if self.is_down:
            self.load_icon.draw(self.surface)
        
        surface.blit(self.surface, self.rect)
    
    def cursor_down(self, button_type=None):
        self.set_image(game.get_image('cursor_press'))
        self.load_icon.start_animation()
        
        self.is_down = True
        self.button_type = button_type
        
    def cursor_up(self):
        self.set_image(game.get_image('cursor_standard'))
        self.is_down = False

class Button(Actor):
    def __init__(self, position, listener):
        super(Button, self).__init__(position)
        
        self.button_up_image = game.get_image('button_up')
        self.button_down_image = game.get_image('button_down')
        self.set_image(self.button_up_image)
        
        self.is_pressed = False
        self.is_key_down = False
        self.pressed_time = 0.0
        self.wait_time = 1.2
        
        self.button_pressed = Event()
        self.button_pressed.subscribe(listener)
        
        game.key_down.subscribe(self.key_down)
    
    def update(self, delta):
        super(Button, self).update(delta)
        
        if self.cursor_over():
            if not self.is_pressed:
                self.press()
        
        elif self.is_pressed:
            self.unpress()
        
        if self.is_pressed:
            self.pressed_time += delta
        
            if self.pressed_time >= self.wait_time:
                self.button_pressed()
                self.pressed_time = 0
    
    def key_down(self, key):
        pass
    
    def cursor_over(self):
        return util.distance(game.get_cursor_position(), self.position) < self.image.get_width() / 2
    
    def press(self):
        self.is_pressed = True
        self.set_image(self.button_down_image)
        game.cursor_down()
        
    def unpress(self):
        self.is_pressed = False
        self.pressed_time = 0.0
        self.set_image(self.button_up_image)
        game.cursor_up()

class CancelButton(Button):
    def __init__(self, position, listener):
        super(CancelButton, self).__init__(position, listener)
        
        self.button_up_image = game.get_image('cancel_up')
        self.button_down_image = game.get_image('cancel_down')
        self.set_image(self.button_up_image)
        self.set_surface(self.image.get_width(),self.image.get_height())
        
    def cursor_over(self):
        cursor_position = game.get_cursor_position()
        return (cursor_position[0] >= self.position[0] - self.image.get_width() / 2 and
                cursor_position[0] <= self.position[0] + self.image.get_width() / 2 and
                cursor_position[1] >= self.position[1] - self.image.get_height() / 2 and
                cursor_position[1] <= self.position[1] + self.image.get_height() / 2)

class HandScreen(Button):
    def __init__(self, position):
        super(Button, self).__init__(position)
        
        self.button_up_image = game.get_image('screen_empty')
        self.button_down_image = game.get_image('screen_active')
        self.set_image(self.button_up_image)
        
        self.is_pressed = False
        self.wait_time = 0
        
        self.hand_surface = pg.Surface((256,256))
        self.hand_rect = self.hand_surface.get_rect()
        
        self.label_text = Line((315, 450), '?', game.get_font('screen_small'))
        self.label_text.set_color(pg.Color(50,240,0))
        
    def update(self, delta):
        super(Button, self).update(delta)
        
        if self.cursor_over():
            if not self.is_pressed:
                self.press()
        
        elif self.is_pressed:
            self.unpress()
            
        if self.is_pressed:
            self.label_text.set_text(detect.detector.get_current_pose())
            self.label_text.update(delta)
    
    def draw(self, surface):
        if not self.is_active: return
        
        self.rect.center = self.position
        self.hand_rect.center = (256, 192)
        
        self.surface.fill(pg.Color(0,0,0,0))
        
        if self.is_pressed:
            frame = detect.detector.get_fixed_frame((256,256), self.position[::-1], (256, 256))
            pg.surfarray.blit_array(self.hand_surface, frame)
            self.surface.blit(self.hand_surface, self.hand_rect)
        
        self.surface.blit(self.image, self.image_rect)
        
        for child in self.children:
            child.draw(surface)
        
        if self.is_pressed:
            self.label_text.draw(self.surface)
        
        surface.blit(self.surface, self.rect)
    
    def cursor_over(self):
        cursor_position = game.get_cursor_position()
        return (cursor_position[0] >= self.position[0] - self.image.get_width() / 2 and
                cursor_position[0] <= self.position[0] + self.image.get_width() / 2 and
                cursor_position[1] >= self.position[1] - self.image.get_height() / 2 and
                cursor_position[1] <= self.position[1] + self.image.get_height() / 2)

    def press(self):
        self.is_pressed = True
        self.set_image(self.button_down_image)
        game.cursor_down(type(self))
        
    def get_pose(self):
        if self.is_pressed:
            return detect.detector.get_current_pose()
        else:
            return None

class PoseTutorial(AnimatedActor):
    def __init__(self, position, activator, pose='a', mode='pingpong', delay=0.5):
        super(PoseTutorial, self).__init__(position, mode, delay)
        
        self.activator = activator
        
        self.pose = pose
        
        self.set_animation(game.get_animation('pose_%s'%pose),
                           (256, 256), 15)
        
        self.load_icon = AnimatedActor((64,64), mode='custom')
        self.load_icon.set_animation(game.get_animation('load'), (64,64), 20)
        self.load_icon_rect = self.load_icon.surface.get_rect()
        
        self.progress_time = 0.0
        self.is_complete = False
        
    def update(self, delta):
        super(PoseTutorial, self).update(delta)
        
        if not self.is_complete:
            if self.activator() == self.pose:
                if self.progress_time < 1:
                    self.progress_time += delta / 2
                else:
                    self.is_complete = True
                    self.progress_time = 0
                    
                    self.set_animation(game.get_animation('pose_complete'),
                                       (256, 256), 15)
                    self.mode = 'one_shot'
            else:
                if self.progress_time > 0:
                    self.progress_time -= delta / 2
            
            self.load_icon.frame_time = self.progress_time
            self.load_icon.update(delta)
        else:
            self.progress_time += delta
            
            if self.progress_time > 2:
                self.is_active = False
        
        
    def draw(self, surface):
        if not self.is_active: return
        
        self.rect.center = self.position
        
        self.surface.fill(pg.Color(0,0,0,0))
        self.surface.blit(self.image, self.image_rect)
        
        for child in self.children:
            child.draw(surface)
            
        if not self.is_complete:
            self.load_icon.draw(self.surface)
        
        surface.blit(self.surface, self.rect)