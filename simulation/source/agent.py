from .entity import Entity

class Agent(Entity):

    def __init__(self, agent_id, name, x, y):
        self.id = agent_id
        self.name = name
        self.x = x
        self.y = y

        
        self.observations = []
        self.actions = []
