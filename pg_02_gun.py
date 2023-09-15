#coding: utf-8
from codeop import CommandCompiler
import pygame

class Gun(object) :
    def __init__(self, screen) :
        self.screen = screen
        self.image = pygame.image.load("пушка.png")
        self.rect = self.image.get_rect()
        self.screen_rect = screen.get_rect()
        self.rect.centerx = self.screen_rect.centerx
        self.rect.bottom = self.screen_rect.bottom

        self.mright = False 
        self.mleft = False 
        self.move_speed = 0.3
        self.center = float(self.rect.centerx)

    def output(self) :
        self.screen.blit(self.image, self.rect)

    def update_gun(self) : 
        """
        ***************************************************************
        * Обновление положения пушки
        * 
        * 
        ***************************************************************
        """ 
        if self.mright :
            if self.rect.centerx >= self.screen_rect.right :
                self.mright = False 
            else :
                self.center += self.move_speed

        if self.mleft :
            if self.rect.centerx > 0 :
                self.center -= self.move_speed
            else :
                self.mleft = False

        self.rect.centerx = self.center
