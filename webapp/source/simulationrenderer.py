import os
from PIL import Image, ImageDraw
from io import BytesIO
import base64
from .spritepool import SpritePool


class SimulationRenderer:
    
    def __init__(self, sprite_sheet_path, sprite_size=64, scale=2, output_dir="output"):
        self.sprite_sheet = Image.open(sprite_sheet_path).convert("RGBA")  # Load the sprite sheet with transparency
        self.sprite_size = sprite_size  # Size of each sprite in the sheet
        self.scale = scale  # Scaling factor for each sprite
        self.output_dir = output_dir  # Directory to save the PNG files

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Load the sprite pool configuration.
        self.__sprite_pool = SpritePool("./assets/sprites/config.json")

        #
        self.__path = None


    def get_sprite(self, sprite_name):
        """Return the sprite from the sprite sheet based on the sprite name."""
        if sprite_name in self.sprite_map:
            x, y = self.sprite_map[sprite_name]
            sprite = self.sprite_sheet.crop(
                (x * self.sprite_size, y * self.sprite_size, (x + 1) * self.sprite_size, (y + 1) * self.sprite_size)
            )
            return sprite.resize((self.sprite_size * self.scale, self.sprite_size * self.scale), Image.NEAREST)
        else:
            raise ValueError(f"Unknown sprite: {sprite_name}")


    def set_path(self, path):
        self.__path = path


    def render(self, render_data, return_base64=False):

        grid_width = render_data['grid_width']
        grid_height = render_data['grid_height']
        grid_cells = render_data['grid_cells']

        sprite_size = 16
        scale = 8

        # Create an empty RGBA image for the grid with transparency support
        image_width = grid_width * sprite_size
        image_height = grid_height * sprite_size
        grid_image = Image.new('RGBA', (image_width, image_height), (0, 0, 0, 0))

        # Make a 2d wall grid.
        walls = [[False for _ in range(grid_width)] for _ in range(grid_height)]
        floors = []
        for cell in grid_cells:
            if cell['sprite'] == "wall":
                walls[cell['y']][cell['x']] = True
            else:
                floors.append((cell['x'], cell['y']))

        # Draw the floor.
        for x, y in floors:
            shadow_string = ""
            if x > 0 and walls[y][x - 1]:
                shadow_string += "l"
            if x < grid_width - 1 and walls[y][x + 1]:
                shadow_string += "r"
            if y < grid_height - 1 and walls[y + 1][x]:
                shadow_string += "u"
            if y > 0 and walls[y - 1][x]:
                shadow_string += "d"

            if "u" in shadow_string and "d" in shadow_string:
                shadow_string = shadow_string.replace("d", "")
            if "l" in shadow_string and "r" in shadow_string:
                shadow_string = shadow_string.replace("r", "")
                
            if shadow_string == "":
                modulo_x = x % 3
                modulo_y = y % 2
                shadow_string = f"{modulo_x}_{modulo_y}"
            elif shadow_string == "d":
                modulo_x = x % 2
                shadow_string = f"d_{modulo_x}"


                 
            print(f"Shadow string: {shadow_string} at {x}, {y}")

            sprite_name = "floor_" + shadow_string
            sprite, _, _ = self.__sprite_pool.get_sprite(sprite_name)
            grid_image.paste(sprite, (x * sprite_size, (grid_height - y - 1) * sprite_size), sprite)

        # Determine the wall type based on the surrounding walls.
        def determine_wall_type(walls, x, y):
            offsets = [
                (-1, 1),
                (0, 1),
                (1, 1),
                (1, 0),
                (1, -1),
                (0, -1),
                (-1, -1),
                (-1, 0),
            ]
            wall_type = ""
            for offset_x, offset_y in offsets:
                new_x = x + offset_x
                new_y = y + offset_y
                if new_x >= 0 and new_x < grid_width and new_y >= 0 and new_y < grid_height:
                    wall_type += "W" if walls[new_y][new_x] else "E"
                else:
                    wall_type += "W"
            return wall_type

        # Render the walls.
        for y in range(grid_height):
            for x in range(grid_width):
                
                # The candidate must be a wall.
                if walls[y][x]:
                    
                    # See if any of the wall render rules apply.
                    wall_type = determine_wall_type(walls, x, y)
                    wall_sprite = "wall_" + wall_type
                    if self.__sprite_pool.has_sprite(wall_sprite):
                        sprite, offset_x, offset_y = self.__sprite_pool.get_sprite(wall_sprite)
                    else:
                        print(f"Unknown wall type: {wall_type}")
                        sprite, offset_x, offset_y = self.__sprite_pool.get_sprite("unknown")
                    render_x = x * sprite_size + offset_x
                    render_y = (grid_height - y - 1) * sprite_size + offset_y
                    grid_image.paste(sprite, (render_x, render_y), sprite)

        def get_objects(types: list[str]):
            assert isinstance(types, list), f"Invalid type: {types}"
            objects = []

            for cell in grid_cells:
                x = cell['x']
                y = cell['y']
                sprite = cell['sprite']
                if sprite in types:
                    objects.append((x, y, sprite))

            assert isinstance(objects, list), f"Invalid objects: {objects}"
            for object in objects:
                assert len(object) == 3, f"Invalid object: {object}"
                assert isinstance(object[0], int), f"Invalid object: {object}"
                assert isinstance(object[1], int), f"Invalid object: {object}"
            return objects

        # Render things on the floor.
        staircases = get_objects(["staircase"])
        for entry in staircases:
            x, y, sprite = entry
            sprite, offset_x, offset_y = self.__sprite_pool.get_sprite(sprite)
            render_x = x * sprite_size + offset_x
            render_y = (grid_height - y - 1) * sprite_size + offset_y
            grid_image.paste(sprite, (render_x, render_y), sprite)
            print(f"Staircase at {x}, {y}")

        # Draw the doors.
        doors = get_objects(["door"])
        for entry in doors:
            x, y, sprite = entry

            # If there is a wall to the left, use the left door sprite.
            if x > 0 and walls[y][x - 1]:
                sprite += "_left"
            # If there is a wall to the right, use the right door sprite.
            elif x < grid_width - 1 and walls[y][x + 1]:
                sprite += "_right"
            # Should not happen.
            else:
                raise ValueError(f"Invalid door position: {x}, {y}")

            sprite, offset_x, offset_y = self.__sprite_pool.get_sprite(sprite)
            render_x = x * sprite_size + offset_x
            render_y = (grid_height - y - 1) * sprite_size + offset_y
            grid_image.paste(sprite, (render_x, render_y), sprite)

        # Draw the sprites.
        sprite_order = ["gold", "trove", "key"]
        for sprite_name in sprite_order:
            for cell in grid_cells:
                if cell['sprite'] == sprite_name:
                    sprite, offset_x, offset_y = self.__sprite_pool.get_sprite(sprite_name)
                    x = cell['x'] * sprite_size + offset_x
                    y = (grid_height - cell['y'] - 1) * sprite_size + offset_y
                    grid_image.paste(sprite, (x, y), sprite)

        # Draw the path.
        if self.__path is not None:

            # Load the path sprite.
            sprite, offset_x, offset_y = self.__sprite_pool.get_sprite("path")

            # Multiply the sprites alpha channel with 0.5 to make it semi-transparent.
            sprite = sprite.convert("RGBA")
            data = sprite.getdata()
            new_data = []
            for item in data:
                item_0 = int(item[0] * 1.0)
                item_1 = int(item[1] * 1)
                item_2 = int(item[2] * 1)
                item_3 = int(item[3] * 0.5)
                new_data.append((item_0, item_1, item_2, item_3))
            sprite.putdata(new_data)
            
            # Draw the path.
            for x, y in self.__path:
                x = x * sprite_size + offset_x
                y = (grid_height - y - 1) * sprite_size + offset_y
                grid_image.paste(sprite, (x, y), sprite)

        # Draw the agent and the enemies.
        sprite_order = ["red", "enemy"]
        cells_with_sprites = []
        for sprite_name in sprite_order:
            for cell in grid_cells:
                if cell['sprite'] == sprite_name:
                    cells_with_sprites.append(cell)
        for cell in cells_with_sprites:
            # Is there another sprite on the same cell?
            there_is_another_sprite = False
            for other_cell in cells_with_sprites:
                if cell != other_cell and cell['x'] == other_cell['x'] and cell['y'] == other_cell['y']:
                    there_is_another_sprite = True
            if there_is_another_sprite and cell['sprite'] == "red":
                additional_offset_x = -6
                additional_offset_y = -2
            elif there_is_another_sprite and cell['sprite'] == "enemy":
                additional_offset_x = 6
                additional_offset_y = 2
            else:
                additional_offset_x = 0
                additional_offset_y = 0
            
            # Render the sprite.
            sprite_name = cell['sprite'] + "_" + cell['state']
            sprite, offset_x, offset_y = self.__sprite_pool.get_sprite(sprite_name)
            x = cell['x'] * sprite_size + offset_x + additional_offset_x
            y = (grid_height - cell['y'] - 1) * sprite_size + offset_y + additional_offset_y
            grid_image.paste(sprite, (x, y), sprite)

        # Scale image with nearest neighbor interpolation.
        image_width *= scale
        image_height *= scale
        grid_image = grid_image.resize((image_width, image_height), Image.NEAREST)

        # Return as base64 encoded string for display in web app. Should work as src for img tag.
        if return_base64:
            buffered = BytesIO()
            grid_image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{image_base64}"
        else:
            assert False, "Not implemented yet"
            return output_path


    def render_old(self, render_data, return_base64=False):
        """Render the grid based on the input render_data and save it as a PNG file."""
        grid_width = render_data['grid_width']
        grid_height = render_data['grid_height']
        grid_cells = render_data['grid_cells']

        # Create an empty RGBA image for the grid with transparency support
        image_width = grid_width * self.sprite_size * self.scale
        image_height = grid_height * self.sprite_size * self.scale
        grid_image = Image.new('RGBA', (image_width, image_height), (0, 0, 0, 0))  # Transparent background

        # Draw each cell in the grid
        for cell in grid_cells:
            sprite = self.get_sprite(cell['sprite'])
            # Calculate the position to place the sprite
            x = cell['x'] * self.sprite_size * self.scale
            y = (grid_height - cell['y'] - 1) * self.sprite_size * self.scale
            grid_image.paste(sprite, (x, y), sprite)  # Use sprite as the mask to handle transparency

            # Draw coordinates for debugging.
            draw = ImageDraw.Draw(grid_image)
            draw.text((x, y), f"{cell['x']}, {cell['y']}", (255, 255, 255), font_size=40)


        # Save the image to a file with transparency (RGBA)
        output_path = os.path.join(self.output_dir, 'grid_render.png')
        grid_image.save(output_path, 'PNG')

        # Return as base64 encoded string for display in web app. Should work as src for img tag.
        if return_base64:
            buffered = BytesIO()
            grid_image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{image_base64}"
        else:
            return output_path