import kivy
kivy.require('1.0.7')

from kivy.uix.gridlayout import GridLayout
from utilities.log_helper import logger


class Client(GridLayout):
    def __init__(self):
        self.defaults = {
            'listening_port': 8000,
            'registering_address': 'localhost:8000',
            'members_address': 'localhost:8001',
            'member_id': 'Some-ID',
            'push_address': 'localhost:8000',
        }
        super().__init__()

    # Get value for an attribute from its input element
    def get(self, key):
        for id_, obj in self.ids.items():
            if id_ == key:
                return obj.text

    def start_listening(self):
        logger.info('Start: {}'.format(self.get('listening_port')))

    def register(self):
        logger.info('Register: {}'.format(self.get('registering_address')))

    def query_members(self):
        logger.info('Query members: {}'.format(self.get('members_address')))

    def push(self):
        logger.info('Push to: {}'.format(self.get('push_address')))

    def push_random(self):
        logger.info('Push to random node')

    def generate_limited_input(self, widget, n):
        # This is used for limiting the input length
        return lambda text, from_undo: text[:n - len(widget.text)]

    def get_widet_id(self, widget):
        for id_, obj in self.ids.items():
            if obj == widget:
                return id_
        return None
