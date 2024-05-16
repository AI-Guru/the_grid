from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import threading
import os
import json
from source.simulation import Simulation

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

clients = {}

# Load the simulation configuration from a file.
simulation_path = "simulations/simulation.json"
if not os.path.exists(simulation_path):
    raise ValueError(f"Simulation file not found: {simulation_path}")
with open(simulation_path) as f:
    simulation_config = json.load(f)
simulation = Simulation(simulation_config)

@app.route('/')
def index():
    return render_template('index.html')

# Get the data for rendering.
@app.route('/api/renderer/data', methods=['GET'])
def get_renderer_data():
    renderer_data = simulation.get_renderer_data()
    return jsonify(renderer_data)


@socketio.on('connect')
def handle_connect():
    # Get the client id from the request headers.
    client_id = request.headers.get("id")

    assert client_id is not None, f"Client ID not provided in arguments {request.args} {request}"
    clients[client_id] = request.sid
    print(f"Client {client_id} connected")


@socketio.on('disconnect')
def handle_disconnect():
    client_id = None
    for cid, sid in clients.items():
        if sid == request.sid:
            client_id = cid
            break
    if client_id:
        del clients[client_id]
        print(f"Client {client_id} disconnected")


@socketio.on('response')
def handle_response(data):
    print(f"Received response from {data['id']}: {data['response']}")
    simulation.add_action(data['id'], data['response'])


def main_loop():
    # Let the simulation step.
    simulation.step()

    # Send a message to each client.
    print(f"Sending messages to clients {clients}")
    for client_id, sid in clients.items():
        socketio.emit('message', {'data': 'Message from server', 'id': client_id}, room=sid)
    
    # Schedule the next loop.
    socketio.start_background_task(timer_callback)

def timer_callback():
    socketio.sleep(1)
    main_loop()

if __name__ == '__main__':
    socketio.start_background_task(main_loop)
    socketio.run(app, host='0.0.0.0', port=5666)
