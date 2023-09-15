import pygame

class Ino(pygame.sprite.Sprite) :
    """
    ***************************************************************
    * Класс одного пришельца
    * 
    * 
    ***************************************************************
    """

    def __init__(self, screen) :
        self.screen = screen
        super(Ino, self).__init__()
        self.screen = screen

        self.image = pygame.image.load(r"D:\18_проектирование\98_PythonShell\Пришелец.png")

        self.rect = self.image.get_rect()
        self.rect.x = self.rect.width
        self.rect.y = self.rect.height

        self.x = float(self.rect.x)
        self.y = float(self.rect.y)

        self.speed_x = 0.1
        self.speed_y = 0.01


    def draw(self) :
        self.screen.blit(self.image, self.rect)

    def move(self) :
        if self.x <= 30 :
            self.speed_x = -self.speed_x
            self.x = 31
        elif self.x >= 650 :
            self.speed_x = -self.speed_x
            self.x = 649
        
        self.x += self.speed_x 
        self.y += self.speed_y

        self.rect.x = self.x
        self.rect.y = self.y




