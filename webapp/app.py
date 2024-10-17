import os
import time
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import gradio as gr
import uvicorn
from dotenv import load_dotenv
import sys
sys.path.append("..")
from source.llmengine import LLMEngine
from source.simulationrenderer import SimulationRenderer
from simulation.source.simulation import Simulation

# Load the environment variables.
load_dotenv(override=True)

# Define the Gradio App as a class
class GradioApp:

    def __init__(self):
        self.demo = None  # This will hold the Gradio Blocks
        self.tabs = None  # This will hold the Gradio Tabs

        # Create the simulation.
        simulation_config_path = "../simulation/simulations/simulation.json"
        assert os.path.exists(simulation_config_path), f"Simulation file not found: {simulation_config_path}"
        self.simulation = Simulation(simulation_config_path)  # Create an instance of the Simulation class

        # Create the simulation renderer.
        sprite_sheet_path = "../simulation/static/spritesheet.png"
        self.simulation_renderer = SimulationRenderer(
            sprite_sheet_path=sprite_sheet_path,
            output_dir="static"
        )

        # Do one step to initialize the simulation.
        self.simulation.step()
        self.environment_image_base64 = self.simulation_renderer.render(self.simulation.get_renderer_data(), return_base64=True)
    
    # Function to build the entire interface
    def build_interface(self):
        with gr.Blocks() as self.demo:
            with gr.Tabs() as self.tabs:
                
                # A tab for the title.
                #with gr.Tab("Title", id=0):
                    # Render Title tab content
                #    start_button, highscore_button = self.render_title_tab()

                # A tab for the game.
                with gr.Tab("Game", id=1):
                    # Render Game tab content
                    elements = self.render_game_tab()
                    instructions_textbox = elements["instructions_textbox"]
                    plan_textbox = elements["plan_textbox"]
                    run_button = elements["run_button"]
                    image_html = elements["image_html"]
                    steps_textbox = elements["steps_textbox"]
                    score_textbox = elements["score_textbox"]
                    inventory_textbox = elements["inventory_textbox"]

                    self.instructions_textbox = instructions_textbox

                # A tab for the high score.
                with gr.Tab("High Score", id=2):
                    # Render High Score tab content
                    back_to_title_button = self.render_highscore_tab()

            # When the start button is clicked, switch to the "Game" tab
            #start_button.click(self.change_tab, inputs=[gr.State(1)], outputs=self.tabs)

            # When the highscore button is clicked, switch to the "High Score" tab
            #highscore_button.click(self.change_tab, inputs=[gr.State(2)], outputs=self.tabs)

            # When the back button in the high score tab is clicked, switch back to the "Title" tab
            back_to_title_button.click(self.change_tab, inputs=[gr.State(0)], outputs=self.tabs)

            #
            run_button.click(
                self.handle_run_button_click,
                inputs=[instructions_textbox],
                outputs=[
                    image_html,
                    plan_textbox,
                    steps_textbox,
                    score_textbox,
                    inventory_textbox
                ],
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
        gr.Markdown("### Game")
        #back_button = gr.Button("Back to Title")

        # Buttons for simulation actions
        with gr.Row():

            # The textbox for instructions, the one for the plan, and the run button.
            with gr.Column():
                instructions_textbox = gr.Textbox("Gehe zum Gold. Hebe es auf. Dann gehe zur Truhe. Lege das Gold dort ab.", lines=10, max_lines=10, label="", placeholder="Anweisungen", interactive=True)
                plan_textbox = gr.Textbox("", lines=10, max_lines=10, label="", placeholder="Plan", interactive=False)
                run_button = gr.Button("Run")

            # Custom HTML for dynamic image update.
            with gr.Column():
                with gr.Row():
                    steps_textbox = gr.Markdown("## Steps: 0")
                    score_textbox = gr.Markdown("## Score: 0")
                inventory_textbox = gr.Markdown("## ")
                image_html = gr.HTML(self.__image_html_string())

        return {
            "instructions_textbox": instructions_textbox,
            "plan_textbox": plan_textbox,
            "run_button": run_button,
            "image_html": image_html,
            "steps_textbox": steps_textbox,
            "score_textbox": score_textbox,
            "inventory_textbox": inventory_textbox
        }
    

    def __image_html_string(self):
        return f'<div id="image-container"><img id="simulation-image" src="{self.environment_image_base64}" width="600px"/></div>'
    

    def handle_run_button_click(self, instructions_textbox):
        instructions = instructions_textbox
        print(instructions)

        # Get the model.
        #llm = get_model("openai", "gpt-4o", temperature=0.5)

        llm_engine = LLMEngine("openai", "gpt-4o", temperature=0.5)

        # Get the agent.
        agents = self.simulation.get_agents()
        agent = agents[0]
        agent_id = agent.id
        agent_observations = self.simulation.get_agent_observations(agent_id)
        
        # Generate a plan.
        actions = llm_engine.generate_plan(agent_observations, instructions)
        assert isinstance(actions, list), f"Invalid actions: {actions}"
        for action in actions:
            assert isinstance(action, str), f"Invalid action: {action}"
            assert action in ["left", "right", "up", "down", "pickup", "drop"], f"Invalid action: {action}"


        def actions_to_string(actions, current_action_index=-1):
            actions_string_list = []
            for i, action in enumerate(actions):
                if i == current_action_index:
                    actions_string_list.append(action.upper())  
                else:
                    actions_string_list.append(action.lower())
            return ", ".join(actions_string_list)
        
        def inventory_to_string(inventory):
            inventory_items = []
            for item in inventory:
                if item.name == "gold":
                    inventory_items.append("🟡")
                else:
                    raise ValueError(f"Unknown item: {item.name}")
            return "".join(inventory_items)
        
        # We have a plan. Update the UI.
        image_html = self.__image_html_string()
        plan_textbox = actions_to_string(actions, -1)
        steps_textbox = gr.Markdown(f"## Steps: {self.simulation.get_step()}")
        score_textbox = gr.Markdown(f"## Score: {self.simulation.get_agent_score(agent_id)}")
        inventory_string = inventory_to_string(self.simulation.get_agent_inventory(agent_id))
        inventory_textbox = gr.Markdown(f"## {inventory_string}")
        yield image_html, plan_textbox, steps_textbox, score_textbox, inventory_textbox

        # TODO: Remove this.
        #return image_html, plan_textbox, steps_textbox, score_textbox, inventory_textbox

        # Execute the plan.
        for action_index, action in enumerate(actions):
            self.simulation.add_action(agent_id, {"action": action})
            self.simulation.step()
            self.environment_image_base64 = self.simulation_renderer.render(self.simulation.get_renderer_data(), return_base64=True)
            image_html = self.__image_html_string()
            plan_textbox = actions_to_string(actions, action_index)
            inventory_string = inventory_to_string(self.simulation.get_agent_inventory(agent_id))
            steps_textbox = gr.Markdown(f"## Steps: {self.simulation.get_step()}")
            score_textbox = gr.Markdown(f"## Score: {self.simulation.get_agent_score(agent_id)}")
            inventory_textbox = gr.Markdown(f"## {inventory_string}")
            yield image_html, plan_textbox, steps_textbox, score_textbox, inventory_textbox
            time.sleep(1)


    # Function to render the High Score tab
    def render_highscore_tab(self):
        gr.Markdown("### High Score")
        back_to_title_button = gr.Button("Back to Title")
        return back_to_title_button


# FastAPI and Gradio integration
fast_api_app = FastAPI()

# Serve static files
fast_api_app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Gradio
gradio_app = GradioApp()  # Create an instance of the GradioApp class
gradio_app.build_interface()  # Build the interface

# Go to second tab.
gradio_app.change_tab(gr.State(1))

# Mount Gradio app onto FastAPI
app = gr.mount_gradio_app(fast_api_app, gradio_app.demo, path="/")

