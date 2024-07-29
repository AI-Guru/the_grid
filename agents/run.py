import os
from source.dummyagent import DummyAgent
from source.llmagent import LlmAgent
import dotenv

dotenv.load_dotenv()

#os.environ["LANGCHAIN_PROJECT"] = "thegrid"

def run():
    client_id = "agent1"
    server_url = 'http://localhost:5666'
    print(f"Starting agent {client_id}")
    agent = LlmAgent(client_id, server_url)
    agent.start()


if __name__ == '__main__':
    run()
