import json
import random
from typing import TypedDict
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from .socketagent import SocketAgent


class AgentGraphState(TypedDict):

    # The observations in raw form.
    observations_raw: dict

    # What the agent observes in text form.
    observations_text: str

    # The agent's memories.
    memories: str

    # The action to perform next.
    action: str


class LlmAgent(SocketAgent):

    def __init__(self, client_id, server_url):
        super().__init__(client_id, server_url)

        # Set up the llm.
        self.__temperature = 0.6
        #self.__base_url = "http://localhost:11434/v1"
        self.__base_url = "http://127.0.0.1:11434/v1"
        self.__api_key = "No"
        self.__model = "gemma2:27b"

        self.__memories = {
            "gold_positions": [],
        }

        # The system message.
        self.__system_message_template = SystemMessagePromptTemplate.from_template(
            "You are a knight in a dungeon. Your goal is to find as much gold as possible."
            " You are supposed to navigate the dungeon and pick up gold wherever you find it."
            " If you see gold, move to that location and pick it up."
        )

        # Create the reasoning graph.
        self.__create_reasoning_graph()


    # This message is called when the agent receives a message from the server.
    def _handle_message(self, data):
        
        # Do a step.
        action = self.__step(data["observations"])

        # Process the message
        response = {"action": action}
        return response
    

    def __step(self, observation, statistics=None):

        observation_text = self.__observations_to_text(observation)
        with open("observation.txt", "w") as f:
            f.write(observation_text)

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
        text += f"- You are at position ({agent_x}, {agent_y}).\n"

        # The elements that the agent sees.
        for cell in observations["cells"]:
            x_relative = cell["x_relative"]
            y_relative = cell["y_relative"]
            relavite_positions = {
                    (0, 0): "center",
                    (0, -1): "up",
                    (0, 1): "down",
                    (-1, 0): "left",
                    (1, 0): "right",
                    (-1, -1): "up and left",
                    (1, -1): "up and right",
                    (-1, 1): "down and left",
                    (1, 1): "down and right",
                }
            relavite_position = relavite_positions[(x_relative, y_relative)]
            assert relavite_position is not None, f"Invalid relative position: {x_relative}, {y_relative}"

            elements = cell["elements"]
            if isinstance(elements, list) and relavite_position != "center":
                elements = ", ".join(elements)
                text += f"- You see these elements at position {relavite_position}: {elements}.\n"
            elif isinstance(elements, list) and relavite_position == "center":
                elements = ", ".join(elements)
                text += f"- You are standing on these elements: {elements}.\n"
            elif elements == "empty" and relavite_position != "center":
                text += f"- You see nothing at position {relavite_position}.\n"
            elif elements == "empty" and relavite_position == "center":
                text += f"- You are standing on nothing.\n"
            else:
                assert False, f"Invalid elements: {elements}"

        return text
    

    def __create_reasoning_graph(self):

        # Create the graph.
        builder = StateGraph(AgentGraphState)

        # A node for updating memories.
        builder.add_node("update_memories", self.__update_memories)
        builder.set_entry_point("update_memories")

        # A node for action selection.
        builder.add_node("decide_action", self.__decide_action)
        builder.add_edge("update_memories", "decide_action")

        # End the graph.
        builder.add_edge("decide_action", END)

        # Get the graph.
        self.__reasoning_graph = builder.compile()


    def __update_memories(self, state):

        # First remove all the gold positions that are not in the observations.
        gold_positions_to_remove = []
        for gold_position in self.__memories["gold_positions"]:
            gold_x, gold_y = gold_position

            for cell in state["observations_raw"]["cells"]:
                x = cell["x"]
                y = cell["y"]

                if x == gold_x and y == gold_y and "gold" not in cell["elements"]:
                    print(f"Removing gold position: {gold_x}, {gold_y}")
                    gold_positions_to_remove.append(gold_position)
                    break
        self.__memories["gold_positions"] = [gold_position for gold_position in self.__memories["gold_positions"] if gold_position not in gold_positions_to_remove]

        # Add all the gold positions that are in the observations.
        for cell in state["observations_raw"]["cells"]:
            x = cell["x"]
            y = cell["y"]
            elements = cell["elements"]

            # If the agent is standing on gold, pick it up.
            if "gold" in elements:
                if (x, y) not in self.__memories["gold_positions"]:
                    print(f"Adding gold position: {x}, {y}")
                    self.__memories["gold_positions"].append((x, y))

        return {}
    

    def __decide_action(self, state):

        human_message_template = HumanMessagePromptTemplate.from_template(
            "Here is a list of your memories:\n {memories}.\n"
            "Here is what you are currently seeing:\n {observations_text}.\n"
            "Please respond with the action you would like to take."
            " Possible actions are: up, down, left, right, pickup, and drop.\n"
            " - up: Moves you up one square. Your y-coordinate decreases by 1.\n"
            " - down: Moves you down one square. Your y-coordinate increases by 1.\n"
            " - left: Moves you left one square. Your x-coordinate decreases by 1.\n"
            " - right: Moves you right one square. Your x-coordinate increases by 1.\n"
            " - pickup: Picks up an item at your current location and adds it to your inventory.\n"
            " - drop: Drops an item from your inventory at your current location.\n"
            "There are no more actions available.\n"
            "You cannot move diagonally.\n"
            "You cannot move in a direction if there is a wall in that direction."
            " Please respond with the action you would like to take and why you would like to take that action."
            " You can only pick up an item when you are standing on it, not when you are next to it."
            " You cannot move into a wall."
            " The last word you say should be the action you would like to take."
            " End with \"This is the action I would like to take:\" ACTION"
        )

        action = self.__run_chain(state, self.__system_message_template, human_message_template)
        print(f"Action reply: {action}")
        action = action.split()[-1].strip().replace(".", "").lower()
        print(f"Action: {action}")
        return {"action": action}


    def __run_chain(self, state, system_message_template, human_message_template):

        # Create the chat template that includes the system and human messages.
        chat_template = ChatPromptTemplate.from_messages(
            [
                system_message_template,
                human_message_template,
            ]
        )

        # Create the model.
        llm = ChatOpenAI(
            temperature=self.__temperature,
            base_url=self.__base_url,
            api_key=self.__api_key,
            model=self.__model,
        )

        # Create the output parser.
        output_parser = StrOutputParser()

        # Create and invoke the chain.
        chain = chat_template | llm | output_parser
        new_state = chain.invoke(state)
        return new_state
