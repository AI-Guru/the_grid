import os
import json
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Literal, List, Union
import heapq


class BaseAction(BaseModel):
    reason: str = Field(
        ..., title="Reason", description="The reason for the action."
    )

class MoveAction(BaseAction):
    direction: Literal["up", "down", "left", "right"] = Field(
        ..., title="Direction", description="The direction to move."
    )

class ManipulateAction(BaseAction):
    action: Literal["pickup", "drop"] = Field(
        ..., title="Action", description="The action to perform."
    )

class GotoAction(BaseAction):

    start_x: int = Field(
        ..., title="Start X", description="The start X position."
    )
    start_y: int = Field(
        ..., title="Start Y", description="The start Y position."
    )
    end_x: int = Field(
        ..., title="End X", description="The end X position."
    )
    end_y: int = Field(
        ..., title="End Y", description="The end Y position."
    )


class Plan(BaseModel):
    actions: List[Union[GotoAction, ManipulateAction]] = Field(
        ..., title="Actions", description="The list of actions."
    )

prompt_template_paths = {
    "system": "prompts/system.txt",
    "plan": "prompts/plan.txt",
}


class LLMEngine:

    def __init__(self, llm_provider: str, llm_name: str, temperature: float):
        self.llm_provider = llm_provider
        self.llm_name = llm_name
        self.temperature = temperature


    def generate_plan(self, agent_observations, user_instructions):

        # Load the system prompt template.
        system_prompt_template = PromptTemplate.from_file(prompt_template_paths["system"])
        system_prompt = system_prompt_template.format()

        # Load the work prompt template.
        work_prompt_template = PromptTemplate.from_file(prompt_template_paths["plan"])
        work_prompt = work_prompt_template.format(
            agent_observations=self.__observations_to_text(agent_observations),
            user_instructions=user_instructions
        )

        # Parse the instructions.
        pydantic_parser = PydanticOutputParser(pydantic_object=Plan)
        
        format_instructions = pydantic_parser.get_format_instructions()
        work_prompt += "\n\n" + format_instructions

        messages = [
            ("system", system_prompt),
            ("user", work_prompt),
        ]

        # Get the model and invoke it.
        llm = self.__get_model(self.llm_provider, self.llm_name, temperature=self.temperature)
        response = llm.invoke(messages)
        messages += [("assistant", response)]
        self.__log_messages(messages)
        plan = pydantic_parser.invoke(response)
        for action in plan.actions:
            assert isinstance(action, GotoAction) or isinstance(action, ManipulateAction)
            print(f"Action: {action}")
  
        actions = self.__plan_to_actions(plan, agent_observations)


        # Print the plan as a JSON string.
        return actions


    def __observations_to_text(self, observations):
        text = ""

        # The position of the agent.
        agent_x = observations["me"]["x"]
        agent_y = observations["me"]["y"]
        agent_position_string = f"x={agent_x}, y={agent_y}"
        text += f"- You are at position {agent_position_string}.\n"

        # The elements that the agent stands on.
        for cell in observations["cells"]:
            x = cell["x"]
            y = cell["y"]
            position_str = f"x={x}, y={y}"
            elements = cell["elements"]
            if isinstance(elements, list) and position_str == agent_position_string:
                elements = ", ".join(elements)
                text += f"- You are standing on {elements}.\n"
            elif elements == "empty" and position_str == agent_position_string:
                text += f"- You are standing on nothing.\n"

        # The elements that the agent sees.
        elements_to_represent = ["gold", "trove"]
        for element in elements_to_represent:
            for cell in observations["cells"]:
                x = cell["x"]
                y = cell["y"]
                position_str = f"x={x}, y={y}"
                elements = cell["elements"]
                if element in elements:
                    text += f"- There is {element} at {position_str}.\n"

        # Done.
        print(f"Observations:\n{text}")
        return text
    

    def __plan_to_actions(self, plan, agent_observations):
        
        # Find the obstacle positions.
        obstacle_positions = []
        for cell in agent_observations["cells"]:
            x = cell["x"]
            y = cell["y"]
            elements = cell["elements"]
            if isinstance(elements, list) and "wall" in elements:
                obstacle_positions.append((x, y))
        
        # Turn the plan into actions.
        actions = []
        for plan_action in plan.actions:

            # Do pathplanning for goto actions.
            if isinstance(plan_action, GotoAction):
                start_x = plan_action.start_x
                start_y = plan_action.start_y
                end_x = plan_action.end_x
                end_y = plan_action.end_y
                print(f"Finding path from {start_x}, {start_y} to {end_x}, {end_y} with obstacles {obstacle_positions}")
                path, _ = find_route(start_x, start_y, end_x, end_y, obstacle_positions)
                print(f"Path: {path}")
                if path is None:
                    raise ValueError(f"Could not find a path from {start_x}, {start_y} to {end_x}, {end_y}.")
                for (x1, y1), (x2, y2) in zip(path[:-1], path[1:]):
                    if x1 == x2 and y1 == y2 - 1:
                        actions.append("up")
                    elif x1 == x2 and y1 == y2 + 1:
                        actions.append("down")
                    elif x1 == x2 - 1 and y1 == y2:
                        actions.append("right")
                    elif x1 == x2 + 1 and y1 == y2:
                        actions.append("left")
                    else:
                        raise ValueError(f"Invalid path from {x1}, {y1} to {x2}, {y2}.")

            # Add the manipulate actions.
            elif isinstance(plan_action, ManipulateAction):
                if plan_action.action == "pickup":
                    actions.append("pickup")
                elif plan_action.action == "drop":
                    actions.append("drop")
            
            # Invalid action.
            else:
                raise ValueError(f"Invalid action: {plan_action}.")

        # Check the actions. If they are okay, return them.
        for action in actions:
            assert action in ["up", "down", "left", "right", "pickup", "drop"]
        print(f"Actions: {actions}")
        return actions
    

    def __log_messages(self, messages):

        messages_path = "output/messages.md"

        # Append the messages to the file.
        with open(messages_path, "a") as file:

            # Add the timestamp.
            file.write(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            for role, message in messages:
                file.write(f"## {role.upper()}\n\n{message}\n\n")


    def __get_model(self, model_provider, model_name, temperature=0.5):
        """
        Get a model.
        :param model_provider: The model provider.
        :param model_name: The model name.
        :param temperature: The temperature.
        :return: The model.
        """

        assert isinstance(model_provider, str)
        assert isinstance(model_name, str)

        def raise_if_not_set(environment_variables):
            for env_var in environment_variables:
                if env_var not in os.environ:
                    raise ValueError(f"{env_var} environment variable is not set.")

        if model_provider == "openai":
            raise_if_not_set(["OPENAI_API_KEY"])
            return ChatOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name=model_name,
                temperature=temperature,
            )
        elif model_provider == "ollama":
            return ChatOpenAI(
                base_url="http://localhost:11434/v1" if "OLLAMA_OPENAI_BASE" not in os.environ else os.getenv("OLLAMA_OPENAI_BASE"),
                api_key="ollama",
                model_name=model_name,
                temperature=temperature,
            )
        elif model_provider == "anthropic":
            raise_if_not_set(["ANTHROPIC_API_KEY"])
            return ChatAnthropic(
                model=model_name,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                temperature=temperature,
                max_tokens=8192,
            )
        else:
            raise ValueError(f"Model provider {model_provider} not supported.")


def find_route(start_x, start_y, end_x, end_y, obstacle_positions):

    class Node:
        def __init__(self, x, y, parent=None):
            self.x = x
            self.y = y
            self.parent = parent
            self.g = 0
            self.h = 0
            self.f = 0

        def __eq__(self, other):
            return self.x == other.x and self.y == other.y

        def __lt__(self, other):
            return self.f < other.f

    def heuristic(node, end_node):
        return abs(node.x - end_node.x) + abs(node.y - end_node.y)

    open_list = []
    closed_list = set()
    obstacle_set = set(obstacle_positions)

    start_node = Node(start_x, start_y)
    end_node = Node(end_x, end_y)

    heapq.heappush(open_list, start_node)

    while open_list:
        current_node = heapq.heappop(open_list)
        closed_list.add((current_node.x, current_node.y))

        if current_node == end_node:
            path = []
            while current_node:
                path.append((current_node.x, current_node.y))
                current_node = current_node.parent
            return path[::-1], len(path)

        children = []
        for new_position in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            node_position = (current_node.x + new_position[0], current_node.y + new_position[1])

            if node_position in closed_list or node_position in obstacle_set:
                continue

            new_node = Node(node_position[0], node_position[1], current_node)
            children.append(new_node)

        for child in children:
            if (child.x, child.y) in closed_list or (child.x, child.y) in obstacle_set:
                continue

            child.g = current_node.g + 1
            child.h = heuristic(child, end_node)
            child.f = child.g + child.h

            if any(open_node for open_node in open_list if child == open_node and child.g > open_node.g):
                continue

            heapq.heappush(open_list, child)

    return None, 0