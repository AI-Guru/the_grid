import random
from .socketagent import SocketAgent

class HumanAgent(SocketAgent):

    def __init__(self, client_id, server_url):
        super().__init__(client_id, server_url)
        self.next_action = "skip"

    def _handle_message(self, data):
        
        # Process the message
        response = {"action": self.next_action}
        self.next_action = "skip"
        return response