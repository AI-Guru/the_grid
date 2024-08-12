from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit
import threading
import os
import json
from source.simulation import Simulation

class Server:
    
    def __init__(self, simulation_config_path, secret_key='secret!'):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = secret_key
        self.socketio = SocketIO(self.app)
        self.clients = {}
        self.sleep_time = 0.1

        # Statistics.
        self.durations = []
        self.average_duration = 0

        # Load simulation configuration
        if not os.path.exists(simulation_config_path):
            raise ValueError(f"Simulation file not found: {simulation_config_path}")
        with open(simulation_config_path) as f:
            self.simulation_config = json.load(f)
        self.simulation = Simulation(self.simulation_config)

        # Register routes and event handlers
        self.app.route('/')(self.index)
        self.app.route('/static/<path:filename>', methods=['GET'])(self.serve_static_file)
        self.app.route('/api/renderer/data', methods=['GET'])(self.get_renderer_data)
        self.socketio.on_event('connect', self.handle_connect)
        self.socketio.on_event('disconnect', self.handle_disconnect)
        self.socketio.on_event('response', self.handle_response)

    def index(self):
        return render_template('index.html')

    def get_renderer_data(self):
        # Get the render data.
        renderer_data = self.simulation.get_renderer_data()

        # Add statistics to the data.
        renderer_data["statistics"] = {
            "current_step": self.simulation.simulation_step,
            "average_duration": f"{self.average_duration:.2f}",
        }

        return jsonify(renderer_data)
    
    def serve_static_file(self, filename):
        return send_from_directory('static', filename)

    def handle_connect(self):
        # Get the client id from the request headers.
        client_id = request.headers.get("id")
        assert client_id is not None, f"Client ID not provided in arguments {request.args} {request}"
        self.clients[client_id] = request.sid
        print(f"Client {client_id} connected")

    def handle_disconnect(self):
        client_id = None
        for cid, sid in self.clients.items():
            if sid == request.sid:
                client_id = cid
                break
        if client_id:
            del self.clients[client_id]
            print(f"Client {client_id} disconnected")

    def handle_response(self, data):
        print(f"Received response from {data['id']}: {data['response']}")
        self.simulation.add_action(data['id'], data['response'])

    def main_loop(self):

        if self.simulation.is_finished():
            self.durations.append(self.simulation.simulation_step)
            self.average_duration = sum(self.durations) / len(self.durations)
            self.simulation = Simulation(self.simulation.config)

        # Let the simulation step
        self.simulation.step()

        # Send a message to each client
        print(f"Sending messages to clients {self.clients}")
        for client_id, sid in self.clients.items():
            observations = self.simulation.get_agent_observations(client_id)
            self.socketio.emit("message", {"observations": observations, "id": client_id}, room=sid)

        # Schedule the next loop
        self.socketio.start_background_task(self.timer_callback)

    def timer_callback(self):
        self.socketio.sleep(self.sleep_time)
        self.main_loop()

    def run(self, host='0.0.0.0', port=5666):
        self.socketio.start_background_task(self.main_loop)
        self.socketio.run(self.app, host=host, port=port)

if __name__ == '__main__':
    server = Server(simulation_config_path="simulations/simulation.json")
    server.run()
