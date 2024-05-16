from .entity import Entity

class Agent(Entity):
    def __init__(self, agent_id, character, x, y):
        self.id = agent_id
        self.character = character
        self.x = x
        self.y = y

        
        self.observations = []
        self.actions = []

    def add_observation(self, observation):
        self.observations.append(observation)

    def add_action(self, action):
        self.actions.append(action)