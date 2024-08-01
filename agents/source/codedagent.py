import random
import json
import heapq

from .socketagent import SocketAgent

class CodedAgent(SocketAgent):


    def __init__(self, client_id, server_url):
        super().__init__(client_id, server_url)




    def _handle_message(self, data):

        # Get the current position of the agent.
        me_x = data["observations"]["me"]["x"]
        me_y = data["observations"]["me"]["y"]

        # Get the current inventory of the agent.
        inventory = data["observations"]["inventory"]

        self.__gold_positions = []
        self.__obstacle_positions = []

        # Update the gold_positions and obstacle_positions.
        for cell in data["observations"]["cells"]:
            x = cell["x"]
            y = cell["y"]
            elements = cell["elements"]
            coordinates = (x, y)

            # Delete the coordinates from the list of gold_positions and obstacle_positions if they are present.
            if elements == "empty":
                if coordinates in self.__gold_positions:
                    self.__gold_positions.remove(coordinates)
                if coordinates in self.__obstacle_positions:
                    self.__obstacle_positions.remove(coordinates)
                continue

            # Now it is a list.
            for element in elements:
                if element == "wall":
                    self.__obstacle_positions.append((x, y))
                elif element == "gold":
                    self.__gold_positions.append((x, y))
                elif element == "trove":
                    trove_x = x
                    trove_y = y
                else:
                    raise Exception(f"Unknown element: {element}")
                

        # Handle the case when there is no gold on the map and the agent has no gold in the inventory.
        if self.__gold_positions == [] and inventory == []:
            print(f"{self.client_id}: No gold on the map.")
            response = {"action": "none"}
            return response
        

        # Handle gold finding
        if inventory == []:

            # If there is gold in the current cell, pick it up.
            if (me_x, me_y) in self.__gold_positions:
                print(f"{self.client_id}: Found gold at {me_x}, {me_y}.")
                response = {"action": "pickup"}
                return response
            
            # If there is no gold in the current cell, move to the nearest gold.
            gold_routes = []
            for gold_position in self.__gold_positions:
                x, y = gold_position
                route, length = self._find_route(me_x, me_y, x, y, self.__obstacle_positions)
                gold_routes.append([route, length])

            # Find the shortest route.
            shortest_route = min(gold_routes, key=lambda x: x[1]) 
            route = shortest_route[0]

            # Move to the next cell.
            next_cell = route[1]
            next_x, next_y = next_cell
            if next_x > me_x:
                action = "right"
            elif next_x < me_x:
                action = "left"
            elif next_y > me_y:
                action = "down"
            elif next_y < me_y:
                action = "up"
            else:
                print(me_x, me_y, next_x, next_y)
                raise Exception("Unknown action.")
            
            print(f"{self.client_id}: Moving to {next_x}, {next_y}.")
            response = {"action": action}
            return response

        # Find the shortest route to the trove.
        elif inventory == ["gold"]:

            if (me_x, me_y) == (trove_x, trove_y):
                print(f"{self.client_id}: Dropping gold at {me_x}, {me_y}.")
                response = {"action": "drop"}
                return response

            # Find the shortest route to the trove.
            route, length = self._find_route(me_x, me_y, trove_x, trove_y, self.__obstacle_positions)

            # Move to the next cell.
            next_cell = route[1]
            next_x, next_y = next_cell
            if next_x > me_x:
                action = "right"
            elif next_x < me_x:
                action = "left"
            elif next_y > me_y:
                action = "down"
            elif next_y < me_y:
                action = "up"
            else:
                print(me_x, me_y, next_x, next_y)
                raise Exception("Unknown action.")
            
            print(f"{self.client_id}: Moving to the trove at {next_x}, {next_y} with action {action}.")
            response = {"action": action}
            return response



        assert False, "This line should not be reached."
 

    def _find_route(self, start_x, start_y, end_x, end_y, obstacle_positions):
        import heapq

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