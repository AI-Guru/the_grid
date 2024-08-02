import random

class LayoutGenerator:
    
    @staticmethod
    def generate(seed, width, height, obstacle_density, gold_density, agents):

        if seed is not None:
            random.seed(seed)
        
        # Initialize layout with empty spaces
        layout = [['.' for _ in range(width)] for _ in range(height)]
        
        # Fill borders with 'X'
        for i in range(width):
            layout[0][i] = 'X'
            layout[height-1][i] = 'X'
        for i in range(height):
            layout[i][0] = 'X'
            layout[i][width-1] = 'X'
        
        # Calculate number of obstacles and gold pieces
        num_obstacles = int(obstacle_density * (width - 2) * (height - 2))
        num_gold = int(gold_density * (width - 2) * (height - 2))
        
        # Function to place items randomly
        def place_items(symbol, count):
            placed = 0
            while placed < count:
                x = random.randint(1, width - 2)
                y = random.randint(1, height - 2)
                if layout[y][x] == '.':
                    layout[y][x] = symbol
                    placed += 1
        
        # Place obstacles and gold
        place_items('X', num_obstacles)
        place_items('G', num_gold)
        place_items('T', 1)
        
        # Place agents
        for agent_index in range(agents):
            placed = False
            while not placed:
                x = random.randint(1, width - 2)
                y = random.randint(1, height - 2)
                if layout[y][x] == '.':
                    layout[y][x] = str(agent_index + 1)
                    placed = True
        
        # Convert layout to list of strings
        layout =  [' '.join(row) for row in layout]

        for row in layout:
            print(row)

        return layout
