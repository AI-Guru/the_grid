# A grid with with and height of cells. Each cell contains a list of entities.

class Grid:

    def __init__(self, config):

        # Process the config.
        self.raiseIfConfigInvalid(config)

        # Load the config and get the with and height of the grid.
        layout = config["layout"]
        height = len(layout)
        widths = [len(row.replace(" ", "")) for row in layout]
        if len(set(widths)) != 1:
            raise ValueError("All rows in the grid must have the same width")
        width = widths[0]
        del widths

        # Set the cells.
        self.static_cells = [["empty" for _ in range(width)] for _ in range(height)]
        y = 0
        for row in layout:
            row = row.replace(" ", "")
            x = 0
            for cell in row:
                if cell == "X":
                    self.static_cells[y][x] = "wall"
                x += 1
            y += 1


        self.width = width
        self.height = height
        self.cells_entities = [[[] for _ in range(self.width)] for _ in range(self.height)]


    def raiseIfConfigInvalid(self, config):
        if "layout" not in config:
            raise ValueError("Missing 'width' key in grid config")

    def clear_entities(self):
        self.cells_entities = [[[] for _ in range(self.width)] for _ in range(self.height)]

    def add_entity(self, entity, x, y):
        self.cells_entities[y][x].append(entity)

    def get_celltype_at(self, x, y):
        return self.static_cells[y][x]

    def get_entities_at(self, x, y):
        # Include the names of the entities in the list.
        return [entity.name for entity in self.cells_entities[y][x]]


    
