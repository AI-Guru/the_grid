# A grid with with and height of cells. Each cell contains a list of entities.

class Grid:

    def __init__(self, config):

        # Process the config.
        self.raiseIfConfigInvalid(config)
        self.width = config["width"]
        self.height = config["height"]
        self.cells = [[[] for _ in range(self.width)] for _ in range(self.height)]


    def raiseIfConfigInvalid(self, config):
        if "width" not in config:
            raise ValueError("Missing 'width' key in grid config")
        if "height" not in config:
            raise ValueError("Missing 'height' key in grid config")

    def add_entity(self, entity, x, y):
        self.cells[y][x].append(entity)


    
