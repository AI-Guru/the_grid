from .entity import Entity

class Item(Entity):

    def __init__(self, name, x, y):
        super().__init__(name, x, y)
