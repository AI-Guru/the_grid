import threading
from source.dummyagent import DummyAgent


def run():
    client_ids = ["agent1", "agent2"]
    server_url = 'http://localhost:5666'
    
    # Create an agent for each client. Run each in a separate thread.
    for client_id in client_ids:
        thread = threading.Thread(target=run_agent, args=(client_id, server_url))
        thread.start()


def run_agent(client_id, server_url):
    print(f"Starting agent {client_id}")
    agent = DummyAgent(client_id, server_url)
    agent.start()



if __name__ == '__main__':
    run()
