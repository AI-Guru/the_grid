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

        simulation_config_path = "../simulation/simulations/simulation.json"
        assert os.path.exists(simulation_config_path), f"Simulation file not found: {simulation_config_path}"
        self.simulation = Simulation(simulation_config_path)  # Create an instance of the Simulation class

        sprite_sheet_path = "../simulation/static/spritesheet.png"
        self.simulation_renderer = SimulationRenderer(
            sprite_sheet_path=sprite_sheet_path,
            output_dir="static"  # Images will be rendered in the static directory
        )  # Create an instance of the SimulationRenderer class

    # Function to build the entire interface
    def build_interface(self):
        with gr.Blocks() as self.demo:
            with gr.Tabs() as self.tabs:
                
                # A tab for the title.
                #with gr.Tab("Title", id=0):
                #    # Render Title tab content
                #    start_button, highscore_button = self.render_title_tab()

                # A tab for the game.
                with gr.Tab("Game", id=1):
                    # Render Game tab content
                    elements = self.render_game_tab()
                    instructions_textbox = elements["instructions_textbox"]
                    run_button = elements["run_button"]
                    left_button = elements["left_button"]
                    right_button = elements["right_button"]
                    up_button = elements["up_button"]
                    down_button = elements["down_button"]
                    image_html = elements["image_html"]

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

            # When the left button is clicked, execute the left action and update the image.
            left_button.click(self.execute_simulation_action, inputs=[gr.State("left")], outputs=image_html, show_progress=False)
            right_button.click(self.execute_simulation_action, inputs=[gr.State("right")], outputs=image_html, show_progress=False)
            up_button.click(self.execute_simulation_action, inputs=[gr.State("up")], outputs=image_html, show_progress=False)
            down_button.click(self.execute_simulation_action, inputs=[gr.State("down")], outputs=image_html, show_progress=False)

            #
            run_button.click(self.handle_run_button_click, inputs=[instructions_textbox], outputs=None, show_progress=False)

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
            with gr.Column():

                instructions_textbox = gr.Textbox("Gehe drei Felder runter", lines=10, max_lines=10, label="", placeholder="Anweisungen", interactive=True)
                run_button = gr.Button("Run")
                left_button = gr.Button("Left")
                right_button = gr.Button("Right")
                up_button = gr.Button("Up")
                down_button = gr.Button("Down")

            with gr.Column():

                # Custom HTML for dynamic image update
                image_html = gr.HTML('''
                    <div id="image-container">
                        <img id="simulation-image" src="/static/grid_render.png" width="600px" />
                    </div>
                ''')

        return {
            "instructions_textbox": instructions_textbox,
            "run_button": run_button,
            "left_button": left_button,
            "right_button": right_button,
            "up_button": up_button,
            "down_button": down_button,
            "image_html": image_html
        }
    
    def handle_run_button_click(self, instructions_textbox):
        instructions = instructions_textbox
        print(instructions)

        # Get the model.
        #llm = get_model("openai", "gpt-4o", temperature=0.5)

        llm_engine = LLMEngine("openai", "gpt-4o", temperature=0.5)

        plan = llm_engine.generate_plan(self.simulation, instructions)



    def execute_simulation_action(self, action):
        assert action in ["left", "right", "up", "down", "pickup", "drop"], f"Invalid action: {action}"

        # Perform the simulation action
        agents = self.simulation.get_agents()
        agent = agents[0]
        agent_id = agent.id
        self.simulation.add_action(agent_id, {"action": action})
        self.simulation.step()

        # Update the image path with a timestamp to force reload
        new_image_path = self.simulation_renderer.render(self.simulation.get_renderer_data())
        timestamped_path = f"/static/grid_render.png?{int(time.time())}"

        # Update the custom HTML element with the new image
        return f'''
        <div id="image-container">
            <img id="simulation-image" src="{timestamped_path}" width="600px" />
        </div>
        '''

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

