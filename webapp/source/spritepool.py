import os
from PIL import Image, ImageDraw
from io import BytesIO
import json

class SpritePool:
    
    def __init__(self, sprite_pool_config_path):


        
        self.__sprite_pool_config_path = sprite_pool_config_path
        self.__load_sprites()

    def __load_sprites(self):

        # Load the sprite pool configuration.
        if os.path.exists(self.__sprite_pool_config_path):
            sprite_pool_config = json.load(open(self.__sprite_pool_config_path))
        else:
            raise ValueError(f"Invalid sprite pool configuration: {self.__sprite_pool_config_path}")

        # Load the sprites.
        self.__sprites = {}
        self.__sprite_offsets = {}
        for key, entry in sprite_pool_config.items():
            
            # Get the values.
            file = entry["file"]
            tile_size = entry["tile_size"]
            x = entry["x"]
            y = entry["y"]   

            # Get the optional values.
            flip_x = entry.get("flip_x", False)
            flip_y = entry.get("flip_y", False)

            # Load the file and crop the sprite.
            file = os.path.join(os.path.dirname(self.__sprite_pool_config_path), file)
            if not os.path.exists(file):
                raise ValueError(f"Sprite file not found: {file}")
            sprite_sheet = Image.open(file).convert("RGBA")
            sprite = sprite_sheet.crop((x * tile_size, y * tile_size, (x + 1) * tile_size, (y + 1) * tile_size))
            if flip_x:
                sprite = sprite.transpose(Image.FLIP_LEFT_RIGHT)
            if flip_y:
                sprite = sprite.transpose(Image.FLIP_TOP_BOTTOM)
            self.__sprites[key] = sprite

            # Get the offsets.
            offset_x = entry.get("offset_x", 0)
            offset_y = entry.get("offset_y", 0)
            self.__sprite_offsets[key] = (offset_x, offset_y)

        # Add an empty sprite.
        self.__sprites["nil"] = Image.new("RGBA", (16, 16), (0, 0, 0, 0))


    def get_sprite(self, key):
        """Return the sprite based on the key."""

        if key in self.__sprites:
            offset_x, offset_y = self.__sprite_offsets[key]
            return self.__sprites[key], offset_x, offset_y
        # Return an empty sprite if the key is not found.
        else:
            print(f"Sprite not found: {key}")
            return self.__sprites["nil"], 0, 0
           

    def has_sprite(self, key):
        """Return True if the sprite exists."""

        return key in self.__sprites
