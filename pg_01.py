
#encoding: utf-8
import pygame, pg_controls
import sys 

from pg_02_gun import Gun
from pygame.sprite import Group
from pg_ino import Ino




def run() :
    pygame.init()
    screen = pygame.display.set_mode((700, 800))

    pygame.display.set_caption = "DMuzer"
    bg_color = (0,0,0)
    gun = Gun(screen)
    bullets = Group()
    ino = Group()
    ino.add(Ino(screen=screen))
    
    while True :
        pg_controls.events(screen = screen, gun=gun, bullets=bullets)

        pg_controls.update_screen(
                bg_color=bg_color, 
                screen=screen,
                gun=gun, 
                bullets=bullets,
                ino=ino
                )

        
        pg_controls.update_bullets(bullets=bullets)
        pg_controls.update_ino(ino=ino)
        pygame.display.flip()


print("start")
run()