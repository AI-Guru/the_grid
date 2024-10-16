import os
import gradio as gr
import time
from dotenv import load_dotenv
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from simulation.source.simulation import Simulation
from source.simulationrenderer import SimulationRenderer

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
        self.simulation_renderer = SimulationRenderer(sprite_sheet_path=sprite_sheet_path)  # Create an instance of the SimulationRenderer class


    # Function to build the entire interface
    def build_interface(self):
        with gr.Blocks() as self.demo:
            with gr.Tabs() as self.tabs:
                # A tab for the title.
                with gr.Tab("Title", id=0):
                    # Render Title tab content
                    start_button, highscore_button = self.render_title_tab()

                # A tab for the game.
                with gr.Tab("Game", id=1):
                    # Render Game tab content
                    elements = self.render_game_tab()
                    back_button, simulation_output, left_button, right_button, up_button, down_button = elements

                # A tab for the high score.
                with gr.Tab("High Score", id=2):
                    # Render High Score tab content
                    back_to_title_button = self.render_highscore_tab()

            # When the start button is clicked, switch to the "Game" tab
            start_button.click(self.change_tab, inputs=[gr.State(1)], outputs=self.tabs)

            # When the highscore button is clicked, switch to the "High Score" tab
            highscore_button.click(self.change_tab, inputs=[gr.State(2)], outputs=self.tabs)

            # When the back button in the game tab is clicked, switch back to the "Title" tab
            back_button.click(self.change_tab, inputs=[gr.State(0)], outputs=self.tabs)

            # When the back button in the high score tab is clicked, switch back to the "Title" tab
            back_to_title_button.click(self.change_tab, inputs=[gr.State(0)], outputs=self.tabs)

            # When the left button is clicked, execute the left action.
            left_button.click(self.execute_simulation_action, inputs=[gr.State("left")], outputs=simulation_output)
            right_button.click(self.execute_simulation_action, inputs=[gr.State("right")], outputs=simulation_output)
            up_button.click(self.execute_simulation_action, inputs=[gr.State("up")], outputs=simulation_output)
            down_button.click(self.execute_simulation_action, inputs=[gr.State("down")], outputs=simulation_output)


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
        back_button = gr.Button("Back to Title")

        # Render the simulation.
        simulation_output = gr.Image(
            self.simulation_renderer.render(self.simulation.get_renderer_data()),
            show_download_button=False,
            show_fullscreen_button=False,
            show_label=False
        )

        # Add buttons for left, right, up, down.
        left_button = gr.Button("Left")
        right_button = gr.Button("Right")
        up_button = gr.Button("Up")
        down_button = gr.Button("Down")

        return back_button, simulation_output, left_button, right_button, up_button, down_button
    

    def execute_simulation_action(self, action):
        assert action in ["left", "right", "up", "down", "pickup", "drop"], f"Invalid action: {action}"

        action = {
            "action": action
        }

        agents = self.simulation.get_agents()
        agent = agents[0]
        agent_id = agent.id
        self.simulation.add_action(agent_id, action)
        self.simulation.step()

        simulation_output = gr.Image(
            self.simulation_renderer.render(self.simulation.get_renderer_data()),
            show_download_button=False,
            show_fullscreen_button=False,
            show_label=False
        )

        return simulation_output


    # Function to render the High Score tab
    def render_highscore_tab(self):
        gr.Markdown("### High Score")
        back_to_title_button = gr.Button("Back to Title")
        return back_to_title_button

    # Function to launch the app
    def launch(self):
        self.demo.launch()


# Function to run the app
def run_app():
    app = GradioApp()  # Create an instance of the GradioApp class
    app.build_interface()  # Build the interface
    app.launch()  # Launch the app


if __name__ == "__main__":
    run_app()
