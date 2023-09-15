import pygame, sys
from pg_bullet import Bullet

def update_screen(bg_color, screen, gun, bullets, ino) :
        gun.update_gun()

        screen.fill(bg_color)

        for bullet in bullets.sprites() :
            bullet.draw_bullet()

        
        gun.output()
        for i in ino :
            i.draw()


def update_bullets(bullets) :
    bullets.update()

    for bullet in bullets :
        if bullet.rect.bottom <= 0 :
            bullets.remove(bullet)


def update_ino(ino) :
    for i in ino :
        i.move()


            

        

def events(screen, gun, bullets) :
    """
    ***************************************************************
    * Обработка событий
    * 
    * 
    ***************************************************************
    """ 

    for event in pygame.event.get() :
        if event.type == pygame.QUIT :
            sys.exit()

        elif event.type == pygame.KEYDOWN :
            if event.key == pygame.K_d or event.key == pygame.K_RIGHT :
                gun.mright = True
            if event.key == pygame.K_a or event.key == pygame.K_LEFT:
                gun.mleft = True 
            if event.key == pygame.K_ESCAPE :
                sys.exit()
            if event.key == pygame.K_SPACE :
                new_bullet = Bullet(screen, gun=gun)
                bullets.add(new_bullet)
                bullets
                pass 

        elif  event.type == pygame.KEYUP :
            gun.mright = False
            gun.mleft = False