import time
import copy
import random
from .agent import Agent
from .grid import Grid

class Simulation:

    def __init__(self, config):
        self.next_id = 1
        self.running = False
        self.simulation_step = 0
        self.actions = {}

        # Process the config.
        self.raiseIfConfigInvalid(config)
        self.grid = Grid(config["grid"])
        self.agents = {}
        for agent_config in config["agents"]:
            agent = Agent(agent_config["identifier"], agent_config["name"], agent_config["x"], agent_config["y"])
            self.agents[agent.id] = agent
        self.update_interval_seconds = config.get("update_interval_seconds", 1.0)


    def raiseIfConfigInvalid(self, config):
        if "grid" not in config:
            raise ValueError("Missing 'grid' key in simulation config")
        if "update_interval_seconds" in config and not isinstance(config["update_interval_seconds"], (int, float)):
            raise ValueError("Invalid 'update_interval_seconds' value in simulation config")
        if "agents" in config and not isinstance(config["agents"], list):
            raise ValueError("Invalid 'agents' value in simulation config")

    def get_renderer_data(self):
        grid_cells = []
        
        # Add the grid cells to the renderer data.
        for x in range(self.grid.width):
            for y in range(self.grid.height):
                grid_cells.append({
                    "x": x,
                    "y": y,
                    "sprite": "grass",
                })

        # Add the agent cells to the renderer data.
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
        self.grid.clear()
        for agent in self.agents.values():
            self.grid.add_entity(agent, agent.x, agent.y)

        # Update agent observations.
        for agent in self.agents.values():

            # Create the observation.
            agent.observations = self.get_agent_observations(agent.x, agent.y)

    def perform_agent_action(self, agent_id, action):
        print(agent_id, action)
        assert agent_id in self.agents, f"Invalid agent id: {agent_id}, {self.agents.keys()}"
        agent = self.agents[agent_id]

        action = action["action"]
        if action == "up":
            if agent.y > 0:
                agent.y -= 1
        elif action == "down":
            if agent.y < self.grid.height - 1:
                agent.y += 1
        elif action == "left":
            if agent.x > 0:
                agent.x -= 1
        elif action == "right":
            if agent.x < self.grid.width - 1:
                agent.x += 1
        else:
            raise ValueError(f"Invalid action: {action}")


    def get_agent_observations(self, agent_x, agent_y):
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
                entities = self.grid.get_entities_at(x, y)
                if entities == []:
                    continue
                observations["cells"].append({
                    "x": x,
                    "y": y,
                    "entities": entities,
                })

        return observations


    def stop(self):
        self.running = False