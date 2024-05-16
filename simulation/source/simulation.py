import time
from .agent import Agent
from .grid import Grid

class Simulation:

    def __init__(self, config):
        self.next_id = 1
        self.running = False
        self.simulation_step = 0

        # Process the config.
        self.raiseIfConfigInvalid(config)
        self.grid = Grid(config["grid"])
        self.agents = {}
        for agent_config in config["agents"]:
            agent = Agent(agent_config["identifier"], agent_config["character"], agent_config["x"], agent_config["y"])
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
                "sprite": agent.character,
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

    def run(self):
        self.running = True

        while self.running:
            print(f"Simulation step: {self.simulation_step}")
            start_time = time.time()
            self.update()
            self.simulation_step += 1
            elapsed_time = time.time() - start_time
            time_to_sleep = max(0, self.update_interval_seconds - elapsed_time)
            if time_to_sleep == 0:
                print("Simulation is running too slow.")
            else:
                time.sleep(time_to_sleep)

    def update(self):
        # Placeholder for the simulation update logic
        for agent in self.agents.values():
            observation = f"Observation at {time.time()}"
            agent.add_observation(observation)

    def stop(self):
        self.running = False