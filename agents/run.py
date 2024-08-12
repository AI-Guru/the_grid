import os
from source.dummyagent import DummyAgent
from source.llmagent import LlmAgent
from source.simplellmagent import SimpleLlmAgent
from source.codedagent import CodedAgent
import dotenv
import fire

dotenv.load_dotenv()

#os.environ["LANGCHAIN_PROJECT"] = "thegrid"

def run(type:str):
    client_id = "agent1"
    server_url = 'http://localhost:5666'
    print(f"Starting agent {client_id}")

    # Create and start the agent.
    if type == "llm":
        agent = LlmAgent(client_id, server_url)
    elif type == "simplellm":
        agent = SimpleLlmAgent(client_id, server_url)
    elif type == "coded":
        agent = CodedAgent(client_id, server_url)
    else:
        raise ValueError(f"Unknown agent type: {type}")
    agent.start()


if __name__ == '__main__':
    fire.Fire(run)
