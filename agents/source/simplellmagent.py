import json
import random
import time
from typing import TypedDict
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_mistralai.chat_models import ChatMistralAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from .socketagent import SocketAgent
import dotenv
import os

# Load things from the .env file.
dotenv.load_dotenv()
mistral_api_key = os.getenv("MISTRAL_API_KEY")
assert mistral_api_key is not None

class AgentGraphState(TypedDict):

    # The observations in raw form.
    observations_raw: dict

    # What the agent observes in text form.
    observations_text: str

    # The agent's memories.
    memories: str

    # The action to perform next.
    action: str


class SimpleLlmAgent(SocketAgent):

    def __init__(self, client_id, server_url):
        super().__init__(client_id, server_url)

        # Set up the llm.
        self.__temperature = 0.4
        self.__base_url = "http://localhost:11434/v1"
        #self.__base_url = "http://127.0.0.1:11434/v1"
        self.__api_key = "No"
        #self.__model = "gemma2:27b"
        #self.__model = "gemma2:9b"
        #self.__model = "llama3.1:8b"
        #self.__model = "llama3.1:70b"
        self.__model = "mistral-large-latest"

        self.__is_computing = False

        # Create the reasoning graph.
        self.__create_reasoning_graph()


    # This message is called when the agent receives a message from the server.
    def _handle_message(self, data):

        if self.__is_computing:
            return
        
        self.__is_computing = True
        
        # Do a step.
        try:
            action = self.__step(data["observations"])
            self.__is_computing = False
        except Exception as e:
            action = "error"
            print(f"Error: {e}")
            self.__is_computing = False
            raise e


        # Process the message
        response = {"action": action}
        return response
    

    def __step(self, observation, statistics=None):

        observation_text = self.__observations_to_text(observation)

        # Invoke the reasoning graph.
        state = {
            "observations_raw": observation,
            "observations_text": observation_text,
        }
        state = self.__reasoning_graph.invoke(state)

        # Return the action.
        action = state["action"]
        return action
    

    def __observations_to_text(self, observations):
        text = ""

        # The position of the agent.
        agent_x = observations["me"]["x"]
        agent_y = observations["me"]["y"]
        text += f"You are at position ({agent_x}, {agent_y})."
        text += "\n"

        # The elements that the agent sees.
        obstacle_positions = []
        gold_positions = []
        trove_positions = []
        for cell in observations["cells"]:
            if cell["elements"] == "empty":
                continue    
            for element in cell["elements"]:
                if element == "wall":
                    obstacle_positions.append((cell["x"], cell["y"]))
                elif element == "gold":
                    gold_positions.append((cell["x"], cell["y"]))
                elif element == "trove":
                    trove_positions.append((cell["x"], cell["y"]))
                else:
                    raise ValueError(f"Unknown element: {element}")

        # Add the obstacle positions.
        text += "There are obstacles at the following positions: "
        text += ", ".join([f"({x}, {y})" for x, y in obstacle_positions])
        text += "\n"

        # Add the gold positions.
        if len(gold_positions) == 0:
            text += "There is no gold in sight."
        else:
            text += "There is gold at the following positions: "
            text += ", ".join([f"({x}, {y})" for x, y in gold_positions])
        text += "\n"

        # Add the trove positions.
        text += "There are treasure troves at the following positions: "
        text += ", ".join([f"({x}, {y})" for x, y in trove_positions])
        text += "\n"

        # Check if the agent is standing on gold.
        standing_on_gold = False
        for x, y in gold_positions:
            if x == agent_x and y == agent_y:
                standing_on_gold = True
                break
        if standing_on_gold:
            text += "You are standing on gold."
            text += "\n"

        # Check if the agent is standing on a trove.
        standing_on_trove = False
        for x, y in trove_positions:
            if x == agent_x and y == agent_y:
                standing_on_trove = True
                break
        if standing_on_trove:
            text += "You are standing on a treasure trove."
            text += "\n"

        # Add the inventory.
        inventory = observations["inventory"]
        if len(inventory) == 0:
            text += "Your inventory is empty."
        else:
            text += "Your inventory contains the following items: "
            text += ", ".join(inventory)
        text += "\n"

        with open("observations.txt", "w") as f:
            f.write(text)

        return text
    

    def __create_reasoning_graph(self):

        # Create the graph.
        builder = StateGraph(AgentGraphState)

        # A node for action selection.
        builder.add_node("decide_action", self.__decide_action)
        builder.set_entry_point("decide_action")
        #builder.add_edge("update_memories", "decide_action")

        # End the graph.
        builder.add_edge("decide_action", END)

        # Get the graph.
        self.__reasoning_graph = builder.compile()


    def __decide_action(self, state):

        # The system message.
        system_message_template = SystemMessagePromptTemplate.from_template(
            "You are a knight in a dungeon. Your goal is to find as much gold as possible."
            " You are supposed to navigate the dungeon and pick up gold wherever you find it."
            " If you see gold, move to that location and pick it up."
            " There is also a treasure trove in the dungeon where you can drop off the gold you have collected. Drop off the gold at the treasure trove.\n"
            " Possible actions are: up, down, left, right, pickup, and drop.\n"
            " - up: Moves you up one square. Your y-coordinate increases by 1. Example: (3, 4) -> (3, 5).\n"
            " - down: Moves you down one square. Your y-coordinate decreases by 1. Example: (3, 4) -> (3, 3).\n"
            " - left: Moves you left one square. Your x-coordinate decreases by 1. Example: (3, 4) -> (2, 4).\n"
            " - right: Moves you right one square. Your x-coordinate increases by 1. Example: (3, 4) -> (4, 4).\n"
            " - pickup: Picks up an item at your current location and adds it to your inventory.\n"
            " - drop: Drops an item from your inventory at your current location.\n"
            " Here are some examples about relavite coordinates:\n"
            " (5, 4) is to the right of (4, 4).\n"
            " (7, 4) is to the left of (8, 4).\n"
            " (4, 5) is above (4, 4).\n"
            " (1, 3) is below (1, 4).\n"
            "There are no more actions available.\n"
            "You cannot move diagonally.\n"
            "You cannot move in a direction if there is a wall in that direction."
            " If you do not carry gold, go to the nearest gold and pick it up."
            " If you carry gold, go to the nearest treasure trove and drop it off."
            " Please respond with the action you would like to take and why you would like to take that action."
            " You can only pick up an item when you are directly standing on it, not when you are next to it."
            " You cannot move into a wall."
        )

        human_message_template = HumanMessagePromptTemplate.from_template(
            "Here are your observations:\n"
            "{observations_text}.\n"
            "Please respond with the action you would like to take."
            " The last word you say should be the action you would like to take."
            " End with \"This is the action I would like to take:\" ACTION"
        )

        action = self.__run_chain(state, system_message_template, human_message_template)
        print(f"Action reply: {action}")
        action = action.split()[-1].strip().replace(".", "").lower()

        for possible_action in ["down", "left", "right", "pickup", "drop", "up"]:
            if possible_action in action:
                action = possible_action
                print(f"Action: {action}")
                return {"action": action}
            
        raise ValueError(f"Unknown action: {action}")


    def __run_chain(self, state, system_message_template, human_message_template):

        # Create the chat template that includes the system and human messages.
        chat_template = ChatPromptTemplate.from_messages(
            [
                system_message_template,
                human_message_template,
            ]
        )

        # Create the model.
        llm = self.create_model()

        # Create the output parser.
        output_parser = StrOutputParser()

        # Create and invoke the chain.
        chain = chat_template | llm | output_parser
        new_state = chain.invoke(state)
        return new_state

    def create_model(self):
        if "mistral" in self.__model:
            return ChatMistralAI(
                api_key=mistral_api_key,
                model=self.__model,
                temperature=self.__temperature,
            )
        else:
            return ChatOpenAI(
                temperature=self.__temperature,
                base_url=self.__base_url,
                api_key=self.__api_key,
                model=self.__model,
            )