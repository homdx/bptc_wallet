import threading
import kivy
from kivy.uix.gridlayout import GridLayout

import bptc.networking.utils as network_utils

kivy.require('1.0.7')


class KivyCore(GridLayout):
    def __init__(self, network, listening_port):
        self.defaults = {
            'listening_port': listening_port,
            'push_address': 'localhost:8000',
            'registering_address': 'localhost:9000',
            'query_members_address': 'localhost:9001',
            'member_id': 'Some-ID'
        }
        self.network = network
        self.hashgraph = network.hashgraph
        self.me = network.hashgraph.me
        self.defaults['member_id'] = self.me.formatted_name
        self.stop = threading.Event()
        super().__init__()
        self.start_listening()

    # Get value for an attribute from its input element
    def get(self, key):
        for id_, obj in self.ids.items():
            if id_ == key:
                return obj.text
        return self.defaults[key]

    @staticmethod
    def generate_limited_input(widget, n):
        # This is used for limiting the input length
        return lambda text, from_undo: text[:n - len(widget.text)]

    def get_widget_id(self, widget):
        for id_, obj in self.ids.items():
            if obj == widget:
                return id_
        return None

    # --------------------------------------------------------------------------
    # Hashgraph actions
    # --------------------------------------------------------------------------

    def start_listening(self):
        network_utils.start_listening(self.network, self.get('listening_port'))

    def register(self):
        ip, port = self.get('registering_address').split(':')
        network_utils.register(self.me.id, self.get('listening_port'), ip, port)

    def query_members(self):
        ip, port = self.get('query_members_address').split(':')
        network_utils.query_members(self, ip, port)

    def heartbeat(self):
        self.network.heartbeat()

    def push(self):
        ip, port = self.get('push_address').split(':')
        self.network.push_to(ip, int(port))

    def push_random(self):
        self.network.start_background_pushes()
