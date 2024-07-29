import pygame
from source.humanagent import HumanAgent


def run():
    client_id = "agent1"
    server_url = 'http://localhost:5666'

    pygame.init()
    screen = pygame.display.set_mode((100, 100))
    
    print(f"Starting agent {client_id}")
    agent = HumanAgent(client_id, server_url)
    agent.start(wait=False)

    # Game loop.
    while True:
        action = "skip"
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    action = "up"
                elif event.key == pygame.K_DOWN:
                    action = "down"
                elif event.key == pygame.K_LEFT:
                    action = "left"
                elif event.key == pygame.K_RIGHT:
                    action = "right"
                elif event.key == pygame.K_p:
                    action = "pickup"
                elif event.key == pygame.K_d:
                    action = "drop"
                agent.sio.emit('response', {'id': client_id, 'response': {"action": action}})
        agent.next_action = action


if __name__ == '__main__':
    run()
