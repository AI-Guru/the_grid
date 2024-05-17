import time
import copy
import random
from .grid import Grid
from .agent import Agent
from .item import Item


class Simulation:

    def __init__(self, config):
        self.next_id = 1
        self.running = False
        self.simulation_step = 0
        self.actions = {}

        # Process the config.
        self.raiseIfConfigInvalid(config)

        # Greate the grid.
        self.grid = Grid(config["grid"])
        self.agents = {}
        self.entities = []

        # Get the agent and entities positions.
        layout = config["grid"]["layout"]
        agent_positions = []
        entities_positions = []
        y = 0
        for row in layout:
            row = row.replace(" ", "")
            x = 0
            for cell in row:
                if cell in ["1", "2"]:
                    agent_positions += [(x, y)]
                elif cell == "G":
                    entities_positions += [("gold", x, y)]
                x += 1
            y += 1

        # Create the agents.
        for agent_index, agent_config in enumerate(config["agents"]):
            identifier = agent_config.get("identifier")
            name = agent_config.get("name")
            x = agent_positions[agent_index][0]
            y = agent_positions[agent_index][1] 
            agent = Agent(identifier, name, x, y)
            self.agents[identifier] = agent
        self.update_interval_seconds = config.get("update_interval_seconds", 1.0)

        # Create the entities.
        for entity_type, entity_x, entity_y in entities_positions:
            entity = Item(entity_type, entity_x, entity_y)
            self.entities.append(entity)


    def raiseIfConfigInvalid(self, config):
        if "grid" not in config:
            raise ValueError("Missing 'grid' key in simulation config")
        if "update_interval_seconds" in config and not isinstance(config["update_interval_seconds"], (int, float)):
            raise ValueError("Invalid 'update_interval_seconds' value in simulation config")
        if "agents" in config and not isinstance(config["agents"], list):
            raise ValueError("Invalid 'agents' value in simulation config")


    def get_renderer_data(self):
        grid_cells = []

        grid_width = self.grid.width
        grid_height = self.grid.height
        print(grid_width, grid_height)
        
        # Add the grid cells to the renderer data.
        for x in range(grid_width):
            for y in range(grid_height):
                grid_cells.append({
                    "x": x,
                    "y": y,
                    "sprite": self.grid.get_celltype_at(x, y)
                })

        # Add the entities to the renderer data.
        for entity in self.entities:
            grid_cells.append({
                "x": entity.x,
                "y": entity.y,
                "sprite": entity.name,
            })

        # Add the agents to the renderer data.
        for agent in self.agents.values():
            grid_cells.append({
                "x": agent.x,
                "y": agent.y,
                "sprite": agent.name,
            })

        # Return the data for rendering.
        renderer_data = {
            "grid_cells": grid_cells,
        }
        return renderer_data


    def add_agent(self):
        agent_id = self.next_id
        self.agents[agent_id] = Agent(agent_id)
        self.next_id += 1
        return agent_id


    def get_agents(self):
        return list(self.agents.values())


    def get_agent(self, agent_id):
        return self.agents.get(agent_id)

    def add_action(self, agent_id, action):
        self.actions[agent_id] = action

    def get_agent_observations(self, agent_id):
        assert agent_id in self.agents, f"Invalid agent id: {agent_id}"
        agent = self.agents.get(agent_id)
        return agent.observations

    def step(self):

        print(f"Simulation step: {self.simulation_step}")
        start_time = time.time()
        self.update()
        self.simulation_step += 1
        elapsed_time = time.time() - start_time
        time_to_sleep = max(0, self.update_interval_seconds - elapsed_time)
        #if time_to_sleep == 0:
        #    print("Simulation is running too slow.")
        #else:
            #time.sleep(time_to_sleep)

    def update(self):
        # TODO: Execute actions. Use randomness.
        actions_to_execute = copy.deepcopy(self.actions)
        self.actions = {}
        print(actions_to_execute)


        # Shuffle the agents to randomize the order in which they execute their actions.
        agent_ids = list(actions_to_execute.keys())
        random.shuffle(agent_ids)
        for agent_id in agent_ids:
            print(f"Agent {agent_id} is executing action {actions_to_execute[agent_id]}")
            self.perform_agent_action(agent_id, actions_to_execute[agent_id])

        # Update the grid.
        self.grid.clear_entities()
        for entity in self.entities:
            self.grid.add_entity(entity, entity.x, entity.y)
        for agent in self.agents.values():
            self.grid.add_entity(agent, agent.x, agent.y)

        # Update agent observations.
        for agent in self.agents.values():

            # Create the observation.
            agent.observations = self.compute_agent_observations(agent.x, agent.y)


    def perform_agent_action(self, agent_id, action):
        print(agent_id, action)
        assert agent_id in self.agents, f"Invalid agent id: {agent_id}, {self.agents.keys()}"
        agent = self.agents[agent_id]

        action = action["action"]
        action_to_move = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0),
        }

        # Handle movement actions.
        action_failed_cause = None
        if action in action_to_move:
            dx, dy = action_to_move[action]
            new_x = agent.x + dx
            new_y = agent.y + dy

            # Check if the new position is valid.
            if new_x < 0 or new_x >= self.grid.width or new_y < 0 or new_y >= self.grid.height:
                action_failed_cause = "out_of_bounds"

            # Check if the new position is empty on the grid.
            if self.grid.get_celltype_at(new_x, new_y) not in ["empty"]:
                action_failed_cause = "cell_not_empty"

            # Handle failure and success.
            if action_failed_cause is not None:
                print(f"Action failed: {action_failed_cause}")
            else:
                agent.x = new_x
                agent.y = new_y

        else:
            print(f"Invalid action: {action}")


    def compute_agent_observations(self, agent_x, agent_y):
        # Get all the cells in the grid around it. The agent is in the center. The grid is a square.
        # Use the grid size to determine the size of the grid.
        grid_size = 3
        observations = {
            "me": {
                "x": agent_x,
                "y": agent_y,
            },
            "step": self.simulation_step,
            "cells": [],
        }
        for x in range(agent_x - grid_size // 2, agent_x + grid_size // 2 + 1):
            for y in range(agent_y - grid_size // 2, agent_y + grid_size // 2 + 1):
                if x < 0 or x >= self.grid.width or y < 0 or y >= self.grid.height:
                    continue
                elements = []
                cell_type = self.grid.get_celltype_at(x, y)
                if cell_type not in ["empty"]:
                    elements.append(cell_type)
                elements += self.grid.get_entities_at(x, y)
                if elements == []:
                    continue
                observations["cells"].append({
                    "x": x,
                    "y": y,
                    "elements": elements,
                })

        return observations


    def stop(self):
        self.running = False