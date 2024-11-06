import os
import time
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import gradio as gr
import uvicorn
from fastapi import Response
from dotenv import load_dotenv
import logging
import sys
sys.path.append("..")
from source.llmengine import LLMEngine
from source.simulationrenderer import SimulationRenderer
from source.textdictionary import TextDictionary
from simulation.source.simulation import Simulation

# Set the logging level.
logging.getLogger("uvicorn.access").disabled = True

# Load the environment variables.
load_dotenv(override=True)

# Define the Gradio App as a class
class GradioApp:

    def __init__(self):

        # Gradio blocks and tabs.
        self.demo = None
        self.tabs = None

        # The chat messages.
        self.chat_messages = []

        # The text dictionary.
        self.text_dictionary = TextDictionary(language="de")

        # Load the level.
        self.load_level("simple")


    def add_chat_message(self, role, content):
        assert role in ["user", "assistant"], f"Invalid role: {role}"
        new_message = {"role": role, "content": content}
        # Only addd if the last message is not the same.
        if len(self.chat_messages) == 0 or self.chat_messages[-1] != new_message:
            self.chat_messages.append({"role": role, "content": content})

    def clear_chat_messages(self):
        self.chat_messages = []


    def next_level(self):
        if self.level_index_or_name == "simple":
            self.load_level("simple")
        elif isinstance(self.level_index_or_name, int):
            self.load_level(self.level_index_or_name + 1)
        else:
            raise ValueError(f"Invalid level_index_or_name: {self.level_index_or_name}")

    def load_level(self, level_index_or_name):

        # Create the simulation.
        if isinstance(level_index_or_name, int):
            simulation_config_path = f"./levels/level_{level_index_or_name:02d}.json"
        elif isinstance(level_index_or_name, str):
            simulation_config_path = f"./levels/level_{level_index_or_name}.json"
        assert os.path.exists(simulation_config_path), f"Simulation file not found: {simulation_config_path}"
        self.simulation = Simulation(simulation_config_path)  # Create an instance of the Simulation class

        # Create the simulation renderer.
        sprite_sheet_path = "../simulation/static/spritesheet.png"
        self.simulation_renderer = SimulationRenderer(
            sprite_sheet_path=sprite_sheet_path,
            output_dir="static"
        )

        # Set the animation delay.
        self.__animation_delay = 0.2

        # Set the initial messages.
        self.clear_chat_messages()
        if "description" in self.simulation.config:
            self.chat_messages = [{"role": "assistant", "content": self.simulation.config["description"]}]

        # Do one step to initialize the simulation.
        self.simulation.step()
        self.environment_image_base64 = self.simulation_renderer.render(self.simulation.get_renderer_data(), return_base64=True)

        # Store the level_index_or_name.
        self.level_index_or_name = level_index_or_name


    # Function to build the entire interface
    def build_interface(self):

        # JavaScript code to update the image.
        # Every second get the image base64 from the endpoint /simulation/image and update the img with id simulation-image.
        # The server will return a base64 string. Just replace the src attribute of the img tag with the new base64 string.
        # The server response starts with "data:image/png;base64," followed by the base64 string.
        java_script = """
            <script>
                setInterval(function() {    
                    fetch('/simulation/image')
                    .then(response => response.text())
                    .then(data => {
                        var image = document.getElementById("simulation-image-dynamic");
                        console.log(data);
                        image.src = data;
                    });

                }, 1000);
            </script>
        """
            
        with gr.Blocks(head=java_script) as self.demo:

            with gr.Tabs() as self.tabs:
                
                # A tab for the title.
                #with gr.Tab("Title", id=0):
                    # Render Title tab content
                #    start_button, highscore_button = self.render_title_tab()

                # A tab for the game.
                with gr.Tab("Game", id=1):
                    game_tab_elements = self.render_game_tab()

                # A tab for the high score.
                with gr.Tab("High Score", id=2):
                    # Render High Score tab content
                    back_to_title_button = self.render_highscore_tab()

            # Elements that will be updated.
            outputs = [
                game_tab_elements["chat_bot"],
                game_tab_elements["plan_textbox"],
                game_tab_elements["steps_textbox"],
                game_tab_elements["score_textbox"],
                game_tab_elements["inventory_textbox"],
            ]

            # The run button click handler.
            game_tab_elements["run_button"].click(
                self.handle_run_button_click,
                inputs=[
                    game_tab_elements["instructions_textbox"]
                ],
                outputs=outputs,
                show_progress=False
            )

            # Add handlers to the buttons.
            if "left_button" in game_tab_elements:
                game_tab_elements["left_button"].click(
                    self.handle_button_left_click,
                    inputs=[],
                    outputs=outputs,
                    show_progress=False
                )
            if "right_button" in game_tab_elements:
                game_tab_elements["right_button"].click(
                    self.handle_button_right_click,
                    inputs=[],
                    outputs=outputs,
                    show_progress=False
                )
            if "up_button" in game_tab_elements:
                game_tab_elements["up_button"].click(
                    self.handle_button_up_click,
                    inputs=[],
                    outputs=outputs,
                    show_progress=False
                )
            if "down_button" in game_tab_elements:
                game_tab_elements["down_button"].click(
                    self.handle_button_down_click,
                    inputs=[],
                    outputs=outputs,
                    show_progress=False
                )
            if "pickup_button" in game_tab_elements:
                game_tab_elements["pickup_button"].click(
                    self.handle_button_pickup_click,
                    inputs=[],
                    outputs=outputs,
                    show_progress=False
                )
            if "drop_button" in game_tab_elements:
                game_tab_elements["drop_button"].click(
                    self.handle_button_drop_click,
                    inputs=[],
                    outputs=outputs,
                    show_progress=False
                )
            if "attack_button" in game_tab_elements:
                game_tab_elements["attack_button"].click(
                    self.handle_button_attack_click,
                    inputs=[],
                    outputs=outputs,
                    show_progress=False
                )


    # General function to change tabs by index
    def change_tab(self, tab_index):
        return gr.Tabs(selected=tab_index)


    # Function to render the Title tab
    def render_title_tab(self):
        logo_path = os.path.join("assets", "logo.jpg")
        gr.Image(logo_path, show_download_button=False, show_fullscreen_button=False, show_label=False)
        start_button = gr.Button("Start Game")
        highscore_button = gr.Button("View High Scores")
        return start_button, highscore_button


    # Function to render the Game tab
    def render_game_tab(self):

        # Define the return data. This will be used to update the UI.
        elements = {}

        # Buttons for simulation actions
        with gr.Row():

            # The textbox for instructions, the one for the plan, and the run button.
            with gr.Column():
                _ = gr.Markdown("## The Grid")
                elements["chat_bot"] = gr.Chatbot(type="messages", show_label=False, value=self.chat_messages)
                gr.Markdown("## Instructions")
                elements["instructions_textbox"] = gr.Textbox("Gehe zum Gold. Hebe es auf. Dann gehe zur Truhe. Lege das Gold dort ab. Du kanns mehrere Goldstücke aufheben. Wenn du mehrere hast, musst du sie nacheinander ablegen.", lines=4, max_lines=4, label="", placeholder="Anweisungen", interactive=True)
                elements["plan_textbox"] = gr.Textbox("", lines=10, max_lines=10, label="", placeholder="Plan", interactive=False)
                elements["run_button"] = gr.Button("Run")

                # A row for buttons. left right up down pickup drop.
                with gr.Row():
                    elements["left_button"] = gr.Button("⬅️")
                    elements["right_button"] = gr.Button("➡️")
                    elements["up_button"] = gr.Button("⬆️")
                    elements["down_button"] = gr.Button("⬇️")
                with gr.Row():
                    elements["pickup_button"] = gr.Button("✊")
                    elements["drop_button"] = gr.Button("🖐️")
                    elements["attack_button"] = gr.Button("⚔️")

            # Custom HTML for dynamic image update.
            with gr.Column():
                with gr.Row():
                    elements["steps_textbox"] = gr.Markdown("## Steps: 0")
                    elements["score_textbox"] = gr.Markdown("## Score: 0")
                    elements["inventory_textbox"] = gr.Markdown("## ")
                elements["image_html"] = gr.HTML('<div id="image-container" style="width:600px;height:600px;background-color:rgb(36 19 26);"><img id="simulation-image-dynamic" src="" width="600px" height="600px"/></div>')

        return elements

    #def __image_html_string(self):
    #    return f'<div id="image-container" style="width:600px;height:600px;background-color:green;"><img id="simulation-image" src="{self.environment_image_base64}" width="600px" height="600px"/></div>'
    
    # Function to handle the run button click
    def handle_run_button_click(self, instructions_textbox):
        instructions = instructions_textbox

        # Get the LLM engine.
        llm_engine = LLMEngine("openai", "gpt-4o", temperature=0.5)

        # Get the agent.
        agents = self.simulation.get_agents()
        agent = agents[0]
        agent_id = agent.id
        agent_observations = self.simulation.get_agent_observations(agent_id)
        
        # Method to convert actions to string.
        def actions_to_string(actions, current_action_index=-1):
            actions_string_list = []
            for i, action in enumerate(actions):
                assert isinstance(action, dict), f"Invalid action: {action}"
                if "action" not in action:
                    continue
                action = action["action"]
                action = self.text_dictionary.get("action_" + action)
                actions_string_list.append(action)
            return ", ".join(actions_string_list)
        
        # Generate a plan.
        actions = llm_engine.generate_plan(agent_observations, instructions)
        assert isinstance(actions, list), f"Invalid actions: {actions}"
        for action in actions:
            assert isinstance(action, dict), f"Invalid action: {action}"
        content = self.text_dictionary.get("plan_generated").format(actions_to_string(actions))
        self.add_chat_message("assistant", "Ich habe einen Plan erstellt. Hier ist der Plan: " + actions_to_string(actions))
        
        def compile_yield_values():
            chat_bot = self.chat_messages
            plan_textbox = actions_to_string(actions, -1)
            steps_textbox = gr.Markdown(f"## Steps: {self.simulation.get_step()}")
            score_textbox = gr.Markdown(f"## Score: {self.simulation.get_agent_score(agent_id)}")
            inventory_string = self.inventory_to_string(self.simulation.get_agent_inventory(agent_id))
            inventory_textbox = gr.Markdown(f"## {inventory_string}")
            return chat_bot, plan_textbox, steps_textbox, score_textbox, inventory_textbox

        # We have a plan. Update the UI.
        yield compile_yield_values()

        # Execute the plan. Update the UI after each step.
        for action_index, action in enumerate(actions):
            # Execute the action.
            if "action" in action:
                result = self.perform_action(action["action"])
                success = result[0]
                terminated = result[1]
                if terminated:
                    yield result[2:]
                    break
                if not success:
                    self.add_chat_message("assistant", "Die Aktion war nicht erfolgreich. Ich stoppe hier.")
                    yield result[2:]
                    break
                yield result[2:]
                time.sleep(self.__animation_delay)
            elif "path" in action:
                #self.simulation.step()
                path = action["path"]
                self.simulation_renderer.set_path(path)
                self.environment_image_base64 = self.simulation_renderer.render(self.simulation.get_renderer_data(), return_base64=True)
                yield compile_yield_values()
                time.sleep(self.__animation_delay)

            elif "done" in action:
                break
            else:
                raise ValueError(f"Invalid action: {action}")


    def inventory_to_string(self, inventory):
        inventory_items = []
        for item in inventory:
            if item.name == "gold":
                inventory_items.append("🟡")
            else:
                raise ValueError(f"Unknown item: {item.name}")
        return "".join(inventory_items)


    # Function to handle the left button click
    def handle_button_left_click(self):
        return self.perform_action("left")[2:]


    # Function to handle the right button click
    def handle_button_right_click(self):
        return self.perform_action("right")[2:]


    # Function to handle the up button click
    def handle_button_up_click(self):
        return self.perform_action("up")[2:]


    # Function to handle the down button click
    def handle_button_down_click(self):
        return self.perform_action("down")[2:]


    # Function to handle the pickup button click
    def handle_button_pickup_click(self):
        return self.perform_action("pickup")[2:]


    # Function to handle the drop button click
    def handle_button_drop_click(self):
        return self.perform_action("drop")[2:]


    # Function to handle the attack button click
    def handle_button_attack_click(self):
        return self.perform_action("attack")[2:]


    # Function to handle the button click
    def perform_action(self, action):

        # Perform the action.
        agent_id = self.simulation.get_agents()[0].id
        self.simulation.add_action(agent_id, {"action": action})
        events = self.simulation.step()

        # Handle the events.
        success = True
        terminated = False
        for event in events:
            # If the event has out of bounds, then we go to the next level.
            if event["type"] == "exit":
                self.next_level()
                terminated = True
                break

            # If the event has a failure cause, then we show the failure cause.
            if event["action_failure_cause"] is not None:
                action_failure_cause = event["action_failure_cause"]
                content = self.text_dictionary.get("action_failure_cause_" + action_failure_cause)
                self.add_chat_message("assistant", content)
                success = False
                break

        if success and not terminated:
            content = self.text_dictionary.get("action_success")
            self.add_chat_message("assistant", content)

        # Update the UI.
        chat_bot = self.chat_messages
        self.environment_image_base64 = self.simulation_renderer.render(self.simulation.get_renderer_data(), return_base64=True)
        plan_textbox = gr.Markdown("## Plan")
        steps_textbox = gr.Markdown(f"## Steps: {self.simulation.get_step()}")
        score_textbox = gr.Markdown(f"## Score: {self.simulation.get_agent_score(agent_id)}")
        inventory_textbox = gr.Markdown(f"## {self.inventory_to_string(self.simulation.get_agent_inventory(agent_id))}")
        return success, terminated, chat_bot, plan_textbox, steps_textbox, score_textbox, inventory_textbox


    # Function to render the High Score tab
    def render_highscore_tab(self):
        gr.Markdown("### High Score")
        back_to_title_button = gr.Button("Back to Title")
        return back_to_title_button


# FastAPI and Gradio integration
fast_api_app = FastAPI()

# Endpoint to get the image.
@fast_api_app.get("/simulation/image")
def get_simulation_image():
    return Response(content=gradio_app.environment_image_base64, media_type="text/plain")
    return gradio_app.environment_image_base64

# Serve static files
fast_api_app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Gradio
gradio_app = GradioApp()  # Create an instance of the GradioApp class
gradio_app.build_interface()  # Build the interface

# Go to second tab.
gradio_app.change_tab(gr.State(1))

# Mount Gradio app onto FastAPI
app = gr.mount_gradio_app(fast_api_app, gradio_app.demo, path="/")
