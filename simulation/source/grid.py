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

    def clear(self):
        self.cells = [[[] for _ in range(self.width)] for _ in range(self.height)]

    def add_entity(self, entity, x, y):
        self.cells[y][x].append(entity)

    def get_entities_at(self, x, y):
        # Include the names of the entities in the list.
        return [entity.name for entity in self.cells[y][x]]


    
