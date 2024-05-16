import requests
import time
import random

def run():

    agent_id = "1"
    base_url = "http://127.0.0.1:5000/api/agents/"
    observations_url = base_url + f"{agent_id}/observations"
    actions_url = base_url + f"{agent_id}/action"

    actions = [
        "up",
        "down",
        "left",
        "right",
    ]
    
    last_step = -1
    while True:
        try:
            observations = requests.get(observations_url).json()
            step = observations["observations"]["step"]
            if step == last_step:
                time.sleep(0.5)
                continue
            
            print(f"Step: {step}")
            print(observations)
            last_step = step

            # Choose a random action and post it.
            action = {
                "action": random.choice(actions),
            }
            response = requests.post(actions_url, json={"action": action})
        except Exception as e:
            print(e)
            time.sleep(1)



if __name__ == "__main__":
    run()


