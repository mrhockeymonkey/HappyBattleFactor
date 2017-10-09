import pygame
import sys
import os
from pygame.locals import *
from settings import *
from player import Player, Obstacle, Mob, collide_hit_rect, Item
from tilemap import TiledMap, Camera

# alias
vec = pygame.math.Vector2

# HUD functions
def draw_player_health(surf, x, y, pct):
    if pct < 0:
        pct = 0
    
    BAR_LENGTH = 100
    BAR_HEIGHT = 20
    fill = pct * BAR_LENGTH
    outlin_rect = pygame.Rect(x, y, BAR_LENGTH, BAR_HEIGHT)
    fill_rect = pygame.Rect(x, y, fill, BAR_HEIGHT)

    if pct > 0.6:
        col = GREEN
    elif pct > 0.3:
        col = YELLOW
    else:
        col = RED

    pygame.draw.rect(surf, col, fill_rect)
    pygame.draw.rect(surf, WHITE, outlin_rect, 2)

class Game:
    def __init__(self):
        # initiate game
        pygame.init()
        pygame.key.set_repeat(1, 1) # (delay, repeat)
        self.screen = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.draw_debug = DEBUG

        # loading files
        self.load_data()

    def load_data(self):
        
        # check to see if running from source or bundle
        if getattr(sys, 'frozen', False):
            print('running from bundle')
            self.dir = sys._MEIPASS
        else:
            print('running from source')
            self.dir = os.path.dirname(__file__)
        
        self.img_dir = os.path.join(self.dir, 'img')
        self.map_dir = os.path.join(self.dir, 'map')

        print(os.path.join(self.img_dir, PLAYER_IMAGE))
        self.player_image = pygame.image.load(os.path.join(self.img_dir, PLAYER_IMAGE))
        self.bullet_image = pygame.image.load(os.path.join(self.img_dir, BULLET_IMG))
        self.mob_image = pygame.image.load(os.path.join(self.img_dir, MOB_IMAGE))
        
        self.map = TiledMap(os.path.join(self.map_dir, MAP))
        self.map_img = self.map.make_map()
        self.map_rect = self.map_img.get_rect()

        self.gun_flashes = []
        for img in MUZZLE_FLASHES:
            self.gun_flashes.append(pygame.image.load(os.path.join(self.img_dir, img))) #convert alpha??

        self.item_images = {}
        for item in ITEM_IMAGES:
            self.item_images[item] = pygame.image.load(os.path.join(self.img_dir, ITEM_IMAGES[item]))

    def new(self):

        #self.map = Map(self)
        self.camera = Camera(self.map, WINDOWWIDTH, WINDOWHEIGHT)

        # Define sprites
        self.all_sprites = pygame.sprite.LayeredUpdates()
        self.wall_sprites = pygame.sprite.Group()
        self.mob_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        self.item_sprites = pygame.sprite.Group()

        for tile_object in self.map.tmxdata.objects:
            # could calculate center here to be cleaner
            if tile_object.name == 'player':
                self.player = Player(self, tile_object.x , tile_object.y)
            if tile_object.name == 'wall':
                Obstacle(self, tile_object.x, tile_object.y, tile_object.width, tile_object.height)
            if tile_object.name == 'mob':
                Mob(self, tile_object.x, tile_object.y)
            if tile_object.name in ['health']:
                Item(self, vec(tile_object.x, tile_object.y), tile_object.name)
            

        self.run()

    def run(self):
        # Game loop
        while True:
            # clock.tick delays loop enough to stay at the correct FPS
            # dt is how long the previous frame took in seconds, this is used to produce smooth movement independant of frame rate
            self.dt = self.clock.tick(FPS) / 1000
            self.events()
            self.update()
            self.draw()

    def events(self):
        #Game loop - events
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

    def update(self):
        # call the update method on all sprites
        self.all_sprites.update()

        # ???
        self.camera.update(self.player)

        # player hits items
        hits = pygame.sprite.spritecollide(self.player,self.item_sprites, False)
        for hit in hits:
            if hit.type == 'health' and self.player.health < PLAYER_HEALTH:
                hit.kill()
                self.player.health = PLAYER_HEALTH

        # should this move to the mob class????
        # mobs hit player
        hits = pygame.sprite.spritecollide(self.player, self.mob_sprites, False, collide_hit_rect)
        for hit in hits:
            self.player.health -= MOB_DAMAGE
            print(self.player.health)
            hit.vel = vec(0, 0)
            if self.player.health <= 0:
                self.playing = False
            if hits:
                self.player.pos += vec(MOB_KNOCKBACK, 0).rotate(-hits[0].rot)

        # bullets hit mobs
        hits = pygame.sprite.groupcollide(self.mob_sprites, self.bullet_sprites, False, True)
        for hit in hits:
            # decrement health and stall sprite to simulate stopping power of bullet
            hit.health -= BULLET_DAMAGE
            hit.vel = vec(0, 0)
  

    def draw(self):

        # draw map
        self.screen.blit(self.map_img, self.camera.apply(self.map_rect))

        # draw sprites
        for sprite in self.all_sprites:
            if isinstance(sprite, Mob):
                sprite.draw_health()
            self.screen.blit(sprite.image, self.camera.apply(sprite.rect))

        
        # debug 
        if self.draw_debug == True:
            pygame.display.set_caption("FPS: {:.2f}".format(self.clock.get_fps()))
            pygame.draw.rect(self.screen, WHITE, self.camera.apply(self.player.rect), 2) #screen, color, rect, thickness
            pygame.draw.rect(self.screen, RED, self.camera.apply(self.player.hit_rect), 2)
            for sprite in self.mob_sprites:
                pygame.draw.rect(self.screen, WHITE, self.camera.apply(sprite.rect), 2)
                pygame.draw.rect(self.screen, RED, self.camera.apply(sprite.hit_rect), 2)
                #pygame.draw.line(self.screen, RED, sprite.pos, (sprite.pos + sprite.vel * 20)) # target line
            for sprite in self.wall_sprites:
                pygame.draw.rect(self.screen, CYAN, self.camera.apply(sprite.rect), 2)
            for sprite in self.bullet_sprites:
                pygame.draw.rect(self.screen, RED, self.camera.apply(sprite.rect), 2)
        # HUD
        draw_player_health(self.screen, 10, 10, self.player.health / PLAYER_HEALTH)

        # update the screen
        pygame.display.update()


if __name__ == '__main__':
    g = Game()
    while g.running:
        g.new()

pygame.quit()