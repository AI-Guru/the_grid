import time
import copy
import random
import os
import json
import itertools
from .grid import Grid
from .agent import Agent
from .item import Item
from .layoutgenerator import LayoutGenerator


class Simulation:

    def __init__(self, config):
        self.next_id = 1
        self.running = False
        self.simulation_step = 0
        self.actions = {}

        # If config is a file, load it with json.
        if isinstance(config, str) and os.path.exists(config):
            with open(config) as f:
                config = json.load(f)
        
        # Raise an error of it is not a dictionary.
        if not isinstance(config, dict):
            raise ValueError("Invalid simulation config")

        # Process the config.
        self.raiseIfConfigInvalid(config)

        if config["grid"]["type"] == "custom":
            layout = config["grid"]["layout"][::-1]
        else:
            layout = LayoutGenerator.generate(**config["grid"]["parameters"])
        config["grid"]["layout"] = layout

        # Greate the grid.
        self.grid = Grid(config["grid"])
        self.agents = {}
        self.entities = []

        # Get the agent and entities positions.
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
                elif cell == "T":
                    entities_positions += [("trove", x, y)]
                elif cell == "E":
                    entities_positions += [("enemy", x, y)]
                elif cell == "D":
                    entities_positions += [("door", x, y)]
                elif cell == "S":
                    entities_positions += [("staircase", x, y)]
                elif cell == "K":
                    entities_positions += [("key", x, y)]
                elif cell in [".", "X"]:
                    pass
                else:
                    raise ValueError(f"Invalid cell type: {cell}")
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

        # Store the triggers.
        self.triggers = config.get("triggers", [])

        # Store the exit positions.
        self.exit_positions = config.get("exits", [])

        # Set the config.
        self.config = config


    def raiseIfConfigInvalid(self, config):
        if "grid" not in config:
            raise ValueError("Missing 'grid' key in simulation config")
        if "update_interval_seconds" in config and not isinstance(config["update_interval_seconds"], (int, float)):
            raise ValueError("Invalid 'update_interval_seconds' value in simulation config")
        if "agents" in config and not isinstance(config["agents"], list):
            raise ValueError("Invalid 'agents' value in simulation config")


    def get_renderer_data(self, version="v1"):
        if version == "v1":
            return self.get_renderer_data_v1()
        elif version == "v2":
            return self.get_renderer_data_v2()
        else:
            raise ValueError("Invalid version")


    def get_renderer_data_v1(self):
        grid_cells = []

        grid_width = self.grid.width
        grid_height = self.grid.height
        
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
                "state": entity.state,
            })

        # Add the agents to the renderer data.
        for agent in self.agents.values():
            grid_cells.append({
                "x": agent.x,
                "y": agent.y,
                "sprite": agent.name,
                "state": agent.state,
            })

        # Add the agent data.
        agent_data_list = []
        for agent in self.agents.values():
            agent_data = {
                "id": agent.id,
                "x": agent.x,
                "y": agent.y,
                "inventory": [item.name for item in agent.inventory],
                "score": agent.score,
                "action_count": agent.action_count
            }
            agent_data_list.append(agent_data)

        # Return the data for rendering.
        renderer_data = {
            "grid_width": grid_width,
            "grid_height": grid_height,
            "grid_cells": grid_cells,
            "agent_data": agent_data_list
        }
        return renderer_data


    def add_agent(self):
        agent_id = self.next_id
        self.agents[agent_id] = Agent(agent_id)
        self.next_id += 1
        return agent_id


    def get_step(self):
        return self.simulation_step


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
    

    def get_agent_score(self, agent_id):
        assert agent_id in self.agents, f"Invalid agent id: {agent_id}"
        agent = self.agents.get(agent_id)
        return agent.score


    def get_agent_inventory(self, agent_id):
        assert agent_id in self.agents, f"Invalid agent id: {agent_id}"
        agent = self.agents.get(agent_id)
        return agent.inventory


    def step(self):

        print(f"Simulation step: {self.simulation_step}")
        #start_time = time.time()
        events = self.update()
        self.simulation_step += 1
        return events
        #elapsed_time = time.time() - start_time
        #time_to_sleep = max(0, self.update_interval_seconds - elapsed_time)
        #if time_to_sleep == 0:
        #    print("Simulation is running too slow.")
        #else:
            #time.sleep(time_to_sleep)


    def update(self):

        # These are the events that will be returned.
        events = []

        # Clone the actions and clear the actions dictionary.
        actions_to_execute = copy.deepcopy(self.actions)
        self.actions = {}

        # Shuffle the agents to randomize the order in which they execute their actions.
        agent_ids = list(actions_to_execute.keys())
        random.shuffle(agent_ids)
        for agent_id in agent_ids:
            print(f"Agent {agent_id} is executing action {actions_to_execute[agent_id]}")
            action_failure_cause, event = self.perform_agent_action(agent_id, actions_to_execute[agent_id])
            events.append({
                "type": "action",
                "agent_id": agent_id,
                "action": actions_to_execute[agent_id]["action"],
                "action_failure_cause": action_failure_cause,
                "event": event,
            })

        # Handle the triggers.
        events += self.handle_triggers()

        # Handle entity interactions.
        events += self.handle_entity_interactions()

        # Handle the exit positions.
        events += self.handle_exits()

        # Update the grid.
        self.grid.clear_entities()
        for entity in self.entities:
            self.grid.add_entity(entity, entity.x, entity.y)
        for agent in self.agents.values():
            self.grid.add_entity(agent, agent.x, agent.y)

        # Update agent observations.
        for agent in self.agents.values():
            agent.observations = self.compute_agent_observations(agent)

        return events


    def perform_agent_action(self, agent_id, action):
        assert agent_id in self.agents, f"Invalid agent id: {agent_id}, {self.agents.keys()}"
        agent = self.agents[agent_id]

        if action is None:
            raise ValueError("Action is None")
            return

        if agent.state == "dead":
            return "agent_dead", None

        agent.action_count += 1

        # Get the action.
        action = action["action"]
        action_to_move = {
            "up": (0, 1),
            "down": (0, -1),
            "left": (-1, 0),
            "right": (1, 0),
        }

        # Initialize variables.
        action_failed_cause = None
        event = None

        # Handle movement actions.
        if action in action_to_move:
            dx, dy = action_to_move[action]
            new_x = agent.x + dx
            new_y = agent.y + dy

            # Check if the new position is valid.
            if new_x < 0 or new_x >= self.grid.width or new_y < 0 or new_y >= self.grid.height:
                action_failed_cause = "out_of_bounds"

            # Check if the new position is empty on the grid.
            elif self.grid.get_celltype_at(new_x, new_y) not in ["empty"]:
                action_failed_cause = "cell_not_empty"

            # If there is an entity at the new position, handle it.
            else:
                entities = self.grid.get_entities_at(new_x, new_y)
                blocking_entities = ["door"]
                for entity in entities:
                    if isinstance(entity, Item) and entity.name in blocking_entities:
                        action_failed_cause = "entity_blocking"
                        break

            # Handle failure and success.
            if action_failed_cause is not None:
                print(f"Action failed: {action_failed_cause}")
            else:
                agent.x = new_x
                agent.y = new_y

        # Handle pickup action.
        elif action == "pickup":
            entities = self.grid.get_entities_at(agent.x, agent.y)
            item = None
            for entity in entities:
                if isinstance(entity, Item) and entity.name in ["gold"]:
                    item = entity
                    break

            # Success.
            if item is not None:
                agent.inventory.append(item)
                self.entities.remove(item)
                print(f"Agent {agent_id} picked up item {item.name}")
            
            # Failure.
            else:
                action_failed_cause = "no_item"

        # Handle drop action.
        elif action == "drop":
            entities = self.grid.get_entities_at(agent.x, agent.y)
            items = [entity for entity in entities if isinstance(entity, Item)]
            
            is_trove = any([entity.name == "trove" for entity in items])
            first_inventory_item_is_gold = len(agent.inventory) > 0 and agent.inventory[0].name == "gold"

            # Dropping gold in a trove.
            if is_trove and first_inventory_item_is_gold:
                agent.inventory.pop()
                agent.score += 1
                print(f"Agent {agent_id} dropped gold at {agent.x}, {agent.y}")
            
            # Dropping an item on an empty cell.
            elif len(items) == 0 and len(agent.inventory) > 0:
                item = agent.inventory.pop()
                item.x = agent.x
                item.y = agent.y
                self.entities.append(item)
                print(f"Agent {agent_id} dropped item {item.name}")
            else:
                print(f"Agent {agent_id} cannot drop item at {agent.x}, {agent.y} because there are items there")

        else:
            print(f"Invalid action: {action}")

        return action_failed_cause, event

    def handle_triggers(self):

        # These are the events that will be returned.
        events = []

        # Go through all the triggers.
        new_triggers = []
        for trigger in self.triggers:

            # Get the trigger data.
            trigger_when = trigger.get("when")
            trigger_frequency = trigger.get("frequency")
            trigger_type = trigger.get("type")
            
            # If there is no entity with the in the grid, trigger.
            triggered = False
            if trigger_when.startswith("no:"):
                entity_name = trigger_when.split(":")[1]
                entities = [entity for entity in self.entities if entity.name == entity_name]
                if len(entities) == 0:
                    triggered = True
            else:
                raise ValueError("Invalid trigger condition")
            
            if triggered:
                print(f"Triggered: {trigger_type}")
            else:
                new_triggers.append(trigger)
                continue

            # Handle the trigger message.
            if "messages" in trigger:
                events.append({
                    "type": "messages",
                    "messages": trigger["messages"],
                })

            # Handle the trigger.
            if trigger_type.startswith("remove:"):

                # Get the entities and filter for the positions.
                entity_name = trigger_type.split(":")[1]
                entities_to_be_removed = [entity for entity in self.entities if entity.name == entity_name]
                entities_to_be_removed = [entity for entity in entities_to_be_removed if [entity.x, entity.y] in trigger["positions"]]
                assert len(entities_to_be_removed) == len(trigger["positions"]), f"Invalid entities to be removed: {entities_to_be_removed} {trigger['positions']}, {entity_name}"

                # Remove the entities.
                self.entities = [entity for entity in self.entities if entity not in entities_to_be_removed]

            # Should not happen.
            else:
                raise ValueError(f"Invalid trigger type: {trigger_type}")
            
            # Decide if the trigger should be kept.
            if trigger_frequency == "once":
                pass
            else:
                raise ValueError(f"Invalid trigger frequency {trigger_frequency}")

        # Update the triggers.
        self.triggers = new_triggers

        # Return the events.
        return events
    

    def handle_entity_interactions(self):

        # If an agent is on the same cell as an enemy, the agent is killed.
        events = []

        for agent in self.agents.values():
            if agent.state == "normal":
                entities = self.grid.get_entities_at(agent.x, agent.y)
                for entity in entities:
                    if entity.name == "enemy":
                        events.append({
                            "type": "agent_killed",
                            "agent_id": agent.id,
                            "messages": "player_killed_by_enemy",
                        })
                        agent.state = "dead"

        return events

    

    def handle_exits(self):

        events = []
        for agent in self.agents.values():
            for next_level, positions in self.exit_positions.items():
                if [agent.x, agent.y] in positions:
                    events.append({
                        "type": "exit",
                        "agent_id": agent.id,
                        "next_level": next_level,
                    })
                    break
        return events


    def compute_agent_observations(self, agent):

        # Empty observations.
        observations = {
        }

        # Add the agents positions.
        observations["me"] = {
            "x": agent.x,
            "y": agent.y,
        }

        # Add the exits. 
        observations["exits"] = []
        for _, exit_positions in self.exit_positions.items():
            for exit_position in exit_positions:
                observations["exits"].append({
                    "x": exit_position[0],
                    "y": exit_position[1],
                    "x_relative": exit_position[0] - agent.x,
                    "y_relative": exit_position[1] - agent.y,
                })

        # Add the step.
        observations["step"] = self.simulation_step

        # Add the inventory.
        observations["inventory"] = [item.name for item in agent.inventory]

        # Handle the observation mode.
        if "observation" not in self.config:
            raise ValueError("Missing 'observation' key in simulation config")
        if "mode" not in self.config["observation"]:
            raise ValueError("Missing 'mode' key in observation config")

        # Get all the cells in the grid around it. The agent is in the center. The grid is a square.
        if self.config["observation"]["mode"] == "square":
            if "grid_size" not in self.config["observation"]:
                raise ValueError("Missing 'grid_size' key in observation config")
            grid_size = self.config["observation"]["grid_size"]
            if grid_size % 2 == 0:
                raise ValueError("The grid size must be an odd number")
            start_x = agent.x - grid_size // 2
            start_x = max(0, start_x)
            end_x = agent.x + grid_size // 2 + 1
            end_x = min(self.grid.width, end_x)
            start_y = agent.y - grid_size // 2
            start_y = max(0, start_y)
            end_y = agent.y + grid_size // 2 + 1
            end_y = min(self.grid.height, end_y)
            range_x = range(start_x, end_x)
            range_y = range(start_y, end_y)
            cell_coordinates = list(itertools.product(range_x, range_y))

        # Get all the cells in the grid.
        elif self.config["observation"]["mode"] == "all":
            cell_coordinates = list(itertools.product(range(self.grid.width), range(self.grid.height)))

        # Should not happen.
        else:
            raise ValueError("Invalid observation mode")
    
        # Go through all the cells.
        observations["cells"] = []
        for x, y in cell_coordinates:
            elements = []
            cell_type = self.grid.get_celltype_at(x, y)
            if cell_type not in ["empty"]:
                elements.append(cell_type)
            elements += self.grid.get_entity_names_at(x, y)
            if agent.name in elements:
                elements.remove(agent.name)
            if elements == []:
                elements = "empty"
            x_relative = x - agent.x
            y_relative = y - agent.y
            observations["cells"].append({
                "x": x,
                "y": y,
                "x_relative": x_relative,
                "y_relative": y_relative,
                "elements": elements,
            })

        return observations

    def is_finished(self):

        # Return true if there is no more gold in the grid and no agent has gold in its inventory.
        if len([entity for entity in self.entities if entity.name == "gold"]) == 0:
            if all([len(agent.inventory) == 0 for agent in self.agents.values()]):
                return True
            
        return False


    def stop(self):
        self.running = False