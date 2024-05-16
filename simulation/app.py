import os
from flask import Flask, request, jsonify, render_template, abort
from flask_executor import Executor
import threading
import time
import json
from source.agent import Agent
from source.simulation import Simulation
import waitress

app = Flask(__name__)
executor = Executor(app)

# Load the simulation configuration from a file.
simulation_path = "simulations/simulation.json"
if not os.path.exists(simulation_path):
    raise ValueError(f"Simulation file not found: {simulation_path}")
with open(simulation_path) as f:
    simulation_config = json.load(f)

# Create a simulation instance
simulation = Simulation(simulation_config)


def run_simulation():
    print("Starting simulation thread...")

    simulation.step()
    threading.Timer(1, run_simulation).start()


@app.route('/')
def index():
    return render_template('index.html')

# Get the data for rendering.
@app.route('/api/renderer/data', methods=['GET'])
def get_renderer_data():
    renderer_data = simulation.get_renderer_data()
    return jsonify(renderer_data)

@app.route('/api/agents', methods=['GET'])
def get_agents():
    agents = [{'id': agent.id} for agent in simulation.get_agents()]
    return jsonify(agents)

@app.route('/api/agents/<int:agent_id>', methods=['GET'])
def get_agent(agent_id):
    agent = simulation.get_agent(agent_id)
    if agent is None:
        abort(404)
    return jsonify({'id': agent.id})

@app.route('/api/agents/<int:agent_id>/observations', methods=['GET'])
def get_agent_observations(agent_id):
    agent = simulation.get_agent(agent_id)
    if agent is None:
        abort(404)
    return jsonify({'id': agent.id, 'observations': agent.observations})

@app.route('/api/agents/<int:agent_id>/action', methods=['POST'])
def agent_action(agent_id):
    simulation.add_action(agent_id, request.json['action'])
    return jsonify({"status": "cool"}), 201

@app.teardown_appcontext
def shutdown_simulation(exception=None):
    simulation.stop()

if __name__ == '__main__':

    # Run run_simulation in 1 second.
    if not app.debug or (app.debug and os.environ.get('WERKZEUG_RUN_MAIN') == 'true'):
        threading.Timer(1, run_simulation).start()

    app.run(debug=False)

    #threading.Thread(target=run_simulation, daemon=True).start()
    # Use waitress to serve the app
    #waitress.serve(app, host='0.0.0.0', port=8080)
