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
        ..., title="Actions", description="The list of actions. If the user wants actions to be performed."
    )

class Answer(BaseModel):
    answer: str = Field(
        ..., title="Answer", description="The answer to the question. Coordinates are ommited. Instead the answer would include relative positions like 'left', 'right', 'up', 'down'."
    )

class Response(BaseModel):
    response: Union[Plan, Answer] = Field(..., title="Response", description="The response to the user. Either a plan or an answer. It is always an answer when the query is a question.")


prompt_template_paths = {
    "system": "prompts/system.txt",
    "plan": "prompts/plan.txt",
}


class LLMEngine:

    def __init__(self, llm_provider: str, llm_name: str, temperature: float):
        self.llm_provider = llm_provider
        self.llm_name = llm_name
        self.temperature = temperature


    def generate_response(self, agent_observations, user_instructions):

        # Load the system prompt template.
        system_prompt_template = PromptTemplate.from_file(prompt_template_paths["system"])
        system_prompt = system_prompt_template.format()

        # Load the work prompt template.
        work_prompt_template = PromptTemplate.from_file(prompt_template_paths["plan"])
        work_prompt = work_prompt_template.format(
            agent_observations=self.__observations_to_text(agent_observations),
            user_instructions=user_instructions
        )

        # Remove all the lines that start with a hash.
        work_prompt = "\n".join([line for line in work_prompt.split("\n") if not line.strip().startswith("#")])

        # Parse the instructions.
        pydantic_parser = PydanticOutputParser(pydantic_object=Response)
        
        # Create the format instructions.
        format_instructions = pydantic_parser.get_format_instructions()
        work_prompt += "\n\n" + format_instructions

        # Compile the list of messages.
        messages = [
            ("system", system_prompt),
            ("user", work_prompt),
        ]

        # Get the model and invoke it.
        print(f"Using LLM provider {self.llm_provider} and model {self.llm_name}.")
        llm = self.__get_model(self.llm_provider, self.llm_name, temperature=self.temperature)
        response = llm.invoke(messages)
        messages += [("assistant", response)]
        self.__log_messages(messages)
        response = pydantic_parser.invoke(response)
        assert isinstance(response, Response) or isinstance(response, Plan)
        #for action in plan.actions:
        #    assert isinstance(action, GotoAction) or isinstance(action, ManipulateAction)
        print(response.model_dump_json(indent=2))
  
        # Return the actions.
        if isinstance(response.response, Answer):
            return [self.__answer_to_action(response.response, agent_observations)]
        elif isinstance(response.response, Plan):
            actions = self.__plan_to_actions(response.response, agent_observations)
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
        elements_to_represent = ["gold", "trove", "enemy"]
        for element in elements_to_represent:
            for cell in observations["cells"]:
                x = cell["x"]
                y = cell["y"]
                position_str = f"x={x}, y={y}"
                elements = cell["elements"]
                if element in elements:
                    text += f"- There is {element} at {position_str}.\n"

        # The exits.
        for exit in observations["exits"]:
            x = exit["x"]
            y = exit["y"]
            position_str = f"x={x}, y={y}"
            text += f"- There is an exit at {position_str}.\n"

        # Done.
        return text
    

    def __answer_to_action(self, response, agent_observations):
        return {"answer": response.answer}


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
                path, _ = find_route(start_x, start_y, end_x, end_y, obstacle_positions)
                actions.append({"path": path})
                if path is None:
                    raise ValueError(f"Could not find a path from {start_x}, {start_y} to {end_x}, {end_y}.")
                for (x1, y1), (x2, y2) in zip(path[:-1], path[1:]):
                    if x1 == x2 and y1 == y2 - 1:
                        actions.append({"action": "up"})
                    elif x1 == x2 and y1 == y2 + 1:
                        actions.append({"action": "down"})
                    elif x1 == x2 - 1 and y1 == y2:
                        actions.append({"action": "right"})
                    elif x1 == x2 + 1 and y1 == y2:
                        actions.append({"action": "left"})
                    else:
                        raise ValueError(f"Invalid path from {x1}, {y1} to {x2}, {y2}.")

            # Add the manipulate actions.
            elif isinstance(plan_action, ManipulateAction):
                if plan_action.action == "pickup":
                    actions.append({"action": "pickup"})
                elif plan_action.action == "drop":
                    actions.append({"action": "drop"})
            
            # Invalid action.
            else:
                raise ValueError(f"Invalid action: {plan_action}.")

        actions.append({"done": True})

        # Check the actions. If they are okay, return them.
        for action in actions:
            if isinstance(action, dict):
                if "action" in action:
                    assert action["action"] in ["up", "down", "left", "right", "pickup", "drop"]
                elif "path" in action:
                    pass
                elif "done" in action:
                    pass
                else:
                    raise ValueError(f"Invalid action: {action}.")
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