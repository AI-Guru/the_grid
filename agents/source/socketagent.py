import socketio


class SocketAgent:

    def __init__(self, client_id, server_url):
        self.client_id = client_id
        self.server_url = server_url
        self.sio = socketio.Client()

        # Register event handlers
        self.sio.on('connect', self.__on_connect)
        self.sio.on('disconnect', self.__on_disconnect)
        self.sio.on('message', self.__on_message)

    def __on_connect(self):
        print(f"Client {self.client_id} connected to server")


    def __on_disconnect(self):
        print(f"Client {self.client_id} disconnected from server")


    def __on_message(self, data):
        print(f"{self.client_id}: Received message: {data['observations']}")
        response = self._handle_message(data)
        self.sio.emit('response', {'id': self.client_id, 'response': response})


    def _handle_message(self, data):
        raise NotImplementedError("Subclasses must implement this method")


    def start(self, wait=True):
        self.sio.connect(self.server_url, headers={'id': self.client_id})
        if wait:
            self.sio.wait()
