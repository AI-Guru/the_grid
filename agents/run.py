import socketio
import random
import threading

class Agent:

    def __init__(self, client_id, server_url):
        self.client_id = client_id
        self.server_url = server_url
        self.sio = socketio.Client()

        # Register event handlers
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('message', self.on_message)

    def on_connect(self):
        print(f"Client {self.client_id} connected to server")


    def on_disconnect(self):
        print(f"Client {self.client_id} disconnected from server")


    def on_message(self, data):
        print(f"{self.client_id}: Received message: {data['observations']}")
        
        actions = ["up", "down", "left", "right"]
        random_action = random.choice(actions)
        print(f"{self.client_id}: Sending response: {random_action}")

        # Process the message
        response = {"action": random_action}
        self.sio.emit('response', {'id': self.client_id, 'response': response})

    def start(self):
        self.sio.connect(self.server_url, headers={'id': self.client_id})
        self.sio.wait()


def run():
    client_ids = ["agent1", "agent2"]
    server_url = 'http://localhost:5666'
    
    # Create an agent for each client. Run each in a separate thread.
    for client_id in client_ids:
        thread = threading.Thread(target=run_agent, args=(client_id, server_url))
        thread.start()


def run_agent(client_id, server_url):
    print(f"Starting agent {client_id}")
    agent = Agent(client_id, server_url)
    agent.start()



if __name__ == '__main__':
    run()
