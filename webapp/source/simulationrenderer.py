import os
from PIL import Image, ImageDraw

class SimulationRenderer:
    
    def __init__(self, sprite_sheet_path, sprite_size=64, scale=2, output_dir="output"):
        self.sprite_sheet = Image.open(sprite_sheet_path).convert("RGBA")  # Load the sprite sheet with transparency
        self.sprite_size = sprite_size  # Size of each sprite in the sheet
        self.scale = scale  # Scaling factor for each sprite
        self.output_dir = output_dir  # Directory to save the PNG files

        # Map each sprite type to its position in the sprite sheet (x, y)
        self.sprite_map = {
            'empty': (1, 0),
            'red': (2, 0),
            'blue': (3, 0),
            'wall': (4, 0),
            'gold': (0, 0),
            'trove': (0, 1),
            'wumpus': (1, 1),
        }

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

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

    def render(self, render_data):
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

        return output_path