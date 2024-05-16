import os
from flask import Flask, request, jsonify, render_template, abort
import threading
import time
from source.agent import Agent
from source.simulation import Simulation

app = Flask(__name__)
app.config['DEBUG'] = True

simulation_config = {
    "grid": {
        "width": 4,
        "height": 4
    },
    "update_interval_seconds": 1.0,
    "agents": [
        {
            "identifier": 1,
            "character": "red",
            "x": 0,
            "y": 0
        },
        {
            "identifier": 2,
            "character": "blue",
            "x": 3,
            "y": 3
        }
    ]
}


# Create a simulation instance
simulation = Simulation(simulation_config)


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
    agent = simulation.get_agent(agent_id)
    if agent is None:
        abort(404)
    if not request.json or 'action' not in request.json:
        abort(400)
    action = request.json['action']
    agent.add_action(action)
    return jsonify({'id': agent.id, 'action': action}), 201

@app.teardown_appcontext
def shutdown_simulation(exception=None):
    simulation.stop()


def start_simulation_thread():
    print("Starting simulation thread...")
    simulation_thread = threading.Thread(target=simulation.run)
    simulation_thread.daemon = True
    simulation_thread.start()
    print("Simulation thread started.")


if __name__ == '__main__':
    print("Starting app and simulation")
    # Only start the simulation thread if this is the main process
    if not app.debug or (app.debug and os.environ.get('WERKZEUG_RUN_MAIN') == 'true'):
        start_simulation_thread()
    print("Starting app...")
    app.run()
    print("App and simulation running")
