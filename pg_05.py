import pygame as pg
import sys
import random
import numpy as np



class dmBall(pg.sprite.Sprite) :
    def __init__(self, pos=None, velocity = None) :
        pg.sprite.Sprite.__init__(self) 

        self.radius = 15

        self.image = pg.Surface((30,30))
        self.rect = self.image.get_rect()
        pg.draw.rect(self.image, (0,0,0,0),self.rect)
        pg.draw.circle(self.image, (0,128, 15), (15,15), 8)

        # self.image.fill((0,128, 15))
        self.rect = self.image.get_rect()
        if not pos :
            self.rect.centerx = random.randrange(50, 700)
            self.rect.centery = random.randrange(50, 700)
            self.x = self.rect.centerx
            self.y = self.rect.centery

        if not velocity :
            self.speed_x = random .random() * 2 - 1
            self.speed_y = random.random() * 2 - 1

    def update(self, *args, **kwargs) :
        self.x += self.speed_x
        if self.x >= 700 :
            self.speed_x = -self.speed_x
            self.x = 699
        elif self.x <= 100 :
            self.speed_x = - self.speed_x
            self.x = 101

        self.y += self.speed_y
        if self.y >= 700 :
            self.speed_y = - self.speed_y
            self.y = 699
        elif self.y <= 100 :
            self.speed_y = - self.speed_y
            self.y  = 101
        self.rect.center = (self.x, self.y)

    def collide(self, other) :
        
        pg.draw.circle(self.image, (128,0, 0), (15,15), 8)
        v = np.array(other.rect.center) - np.array(self.rect.center)


        vl = np.linalg.norm(v)
        if vl == 0 : return
        ne = v / vl
        speed = np.array([self.speed_x, self.speed_y])
        v_speed = np.dot(ne, speed)
        v_speed_v = speed * v_speed

        speed = speed - 2 * v_speed_v
        self.speed_x, self.speed_y = speed[0], speed[1]
    
        pass

    


g = pg.sprite.Group()

for i in range(10) :
    g.add(dmBall())


pg.init()
screen = pg.display.set_mode((800,800))

bg_color = (0,0,0)
quit = False
while True :
    for event in pg.event.get() :
        if event.type == pg.QUIT :
            sys.exit()

        if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE :
            quit = True

    

    collisions = pg.sprite.groupcollide(g, g, False, False, pg.sprite.collide_circle)
    for c in collisions :
        if len(collisions[c]) > 1 :
            c.collide(collisions[c][1])
            # quit = True  
    screen.fill((0,0,0))
    g.update()
    g.draw(screen)

    # for s in g :
    #     s.draw_s()

    pg.display.flip()



    if quit : break 


print(1)       

