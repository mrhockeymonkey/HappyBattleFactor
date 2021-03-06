import pygame
import pytmx
from pytmx.util_pygame import load_pygame
from settings import *


class TileMap(object):
    def __init__(self, filename):
        tm = pytmx.load_pygame(filename, pixelalpha = True)
        self.width = tm.width * tm.tilewidth
        self.height = tm.height * tm.tileheight
        self.tmxdata = tm

    def _render(self, surface):
        for layer in self.tmxdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = self.tmxdata.get_tile_image_by_gid(gid)
                    if tile:
                        surface.blit(tile, (x * self.tmxdata.tilewidth, y * self.tmxdata.tileheight))

    def make_map(self):
        temp_surface = pygame.Surface((self.width, self.height))
        self._render(temp_surface)
        return temp_surface


class IsoTileMap(object):
    """Isometric maps are more difficult to render becuase translating each cartisian coordinate into a screen 
    co-ordinate is a function of both the cartesian x and cartesian y. This is becuase isometic maps tiles are diamond shaped.

    In tiled it is as if the map is turn 45 degrees to the right

    x ->                            x
    |  |  |  |  |          /    / \   \
    |  |  |  |  |         y   / \ / \ 
    |  |  |  |  |             \ / \ /

    To simplyfy the issue we use Isometric (Staggered) maps, which are a bit more intuitive in that screen x,y values follow
    the same axis as cartesian values, and draw them in a "ZigZag" pattern

    0: / \ / \ / \      # first render all tiles on y=0
    1: \ / \ / \ / \    # then offset by tilewidth/2 and render all tiles on y=1
    2:   \ / \ / \ / \  # then render normally all tiles on y=2
         / \ / \ / \ /    

    Here are some helpful links on the concept:
        - http://clintbellanger.net/articles/isometric_math/
        - https://stackoverflow.com/questions/892811/drawing-isometric-game-worlds"""
    
    def __init__(self, filename):
        self.tmxdata = load_pygame(filename, pixelalpha = True)
        self.width = self.tmxdata.width * self.tmxdata.tilewidth
        self.height = self.tmxdata.height * self.tmxdata.tileheight / 2  #- MAP_CLIPPING['bottom']# halved becuase of staggering
        self.rect = pygame.Rect(0, 0, self.width, self.height)

    def _render(self, surface, layers):
        layer_no = 0
        for layer in self.tmxdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and layer.name in layers:
                y_coordinates = list(range(0, layer.height))
                x_coordinates = list(range(0, layer.width))

                # loopthrough each tile, get the image for that tile and draw
                for cart_y in y_coordinates:
                    for cart_x in x_coordinates:
                        tile = self.tmxdata.get_tile_image(cart_x, cart_y, layer_no)
                        if tile:
                            if cart_y % 2 == 0: #i.e. y is even
                                x_offset = 0
                            else:
                                x_offset = self.tmxdata.tilewidth / 2

                            surf_x = cart_x * self.tmxdata.tilewidth + x_offset
                            surf_y = cart_y * self.tmxdata.tileheight / 2 - MAP_CLIP_TOP
                            surface.blit(tile, (surf_x, surf_y))

            layer_no = layer_no + 1

    def make(self):
        """Render the map into an image that can be draw to screen
        You can specify which layers are used to make the map and is alpha is to be used"""
        self.background = pygame.Surface((self.width, self.height))
        self._render(self.background, ['background', 'midground'])

        
        self.foreground = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self._render(self.foreground, ['foreground'])

        #if alpha:
        #    temp_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        #else:
        #    temp_surface = pygame.Surface((self.width, self.height))
            
        #temp_surface.set_colorkey(BLACK, pygame.RLEACCEL)
        #self._render(temp_surface, layers)
        #self.image = temp_surface
        #self.rect = temp_surface.get_rect()
        #return temp_surface


class Hud(object):
    def __init__(self, player, x, y):
        self.player = player
        self.x = x
        self.y = y
        self.hbar_length = 100
        self.hbar_height = 20
        self.hbar_outline =  pygame.Rect(x, y, self.hbar_length, self.hbar_height)
        self.hbar_outline_col = WHITE
        self.hbar_fill = pygame.Rect(x, y, self.hbar_length, self.hbar_height)
        self.hbar_fill_col = GREEN

    def update(self):
        # calculate percent health player has
        pct = self.player.health / self.player.max_health
        if pct < 0:
            pct = 0

        # based on pct choose color
        if pct > 0.6:
            self.hbar_fill_col = GREEN
        elif pct > 0.3:
            self.hbar_fill_col = YELLOW
        else:
            self.hbar_fill_col = RED

        # update the hud rect that will be drawn
        fill = pct * self.hbar_length
        self.hbar_fill = pygame.Rect(self.x, self.y, fill, self.hbar_height)


class Camera(object):
    """
    The camera is simply a Rect that moves with the player
    As the camera moves other objects are shifted the same amount in the opposite direction (offset)
    to create the feeling that the camera is scrolling through the map
    """
    def __init__(self, map, width, height):
        self.width = width
        self.height = height
        self.offset = pygame.Rect(0, 0, self.width, self.height) # used to move other objects
        self.rect = pygame.Rect(0, 0, self.width, self.height) # used to keep track of viewpoint
        self.map = map

    # given a rect simply shift it the amount the camera has "moved"
    def apply(self, rect):
        """
        Moves a rect relative to the offset
        """
        return rect.move(self.offset.topleft)

    def apply_poly(self, polygon):
        """
        Moves a poly relative to the offset
        """
        return polygon.move(self.offset.topleft[0], self.offset.topleft[1])

    def apply_points(self, points):
        """
        Moves a list of points relative to the offset
        """
        new_points = []
        for p in range(0, len(points)):
            new_x = points[p][0] + self.offset.topleft[0]
            new_y = points[p][1] + self.offset.topleft[1]
            new_points.append((new_x, new_y))
        return new_points

    def update(self, target):
        """
        Updates the pos of the camera based on the target being tracked
        """
        # update the pos of the camera rect
        x = -target.rect.x + int(self.width / 2)
        y = -target.rect.y + int(self.height / 2)

        # limit scrolling to map size
        x = min(0, x) # left
        y = min(0, y) # top
        x = max(-(self.map.width - self.width), x) # right
        y = max(-(self.map.height - self.height), y) # bottom

        self.offset = pygame.Rect(x, y, self.width, self.height)
        self.rect = pygame.Rect(-x, -y, self.width, self.height)
