from .entity import Entity

class Agent(Entity):

    def __init__(self, agent_id, name, x, y):
        super().__init__(name, x, y)
        self.id = agent_id
        self.observations = []
        self.actions = []
        self.inventory = []
        self.score = 0
        self.action_count = 0
