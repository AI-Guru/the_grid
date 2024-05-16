import random
from .socketagent import SocketAgent

class DummyAgent(SocketAgent):

    def _handle_message(self, data):
        
        # Select a random message.
        actions = ["up", "down", "left", "right"]
        random_action = random.choice(actions)
        print(f"{self.client_id}: Sending response: {random_action}")

        # Process the message
        response = {"action": random_action}
        return response