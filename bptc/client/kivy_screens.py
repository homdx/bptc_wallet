import threading
import kivy
from kivy.adapters.listadapter import ListAdapter
from kivy.adapters.simplelistadapter import SimpleListAdapter
from kivy.uix.label import Label
from kivy.uix.listview import ListItemButton, ListView
from kivy.uix.screenmanager import Screen
import bptc
import bptc.utils.network as network_utils

kivy.require('1.0.7')


class KivyScreen(Screen):
    @staticmethod
    def generate_limited_input(widget, n):
        # This is used for limiting the input length
        return lambda text, from_undo: text[:n - len(widget.text)]


class MainScreen(KivyScreen):
    """The main screen of the Kivy App."""

    def __init__(self, network, defaults):
        self.network = network
        self.defaults = defaults

        super().__init__()

        # endless loop that updates information displayed
        def update_user_details():
            self.ids.account_balance_label.text = 'Balance: {} BPTC'.format(self.me.account_balance)
            self.ids.account_name_label.text = '{}'.format(self.me.formatted_name)
            t = threading.Timer(1, update_user_details)
            t.daemon = True
            t.start()

        update_user_details()

    @property
    def hashgraph(self):
        return self.network.hashgraph

    @property
    def me(self):
        return self.network.me


class NewTransactionScreen(KivyScreen):
    """NewTransaction screen of the Kivy App"""

    class MemberListItemButton(ListItemButton):
        def __init__(self, **kwargs):
            self.deselected_color = [1, 1, 1, 1]
            self.selected_color = [0.2, 0.5, 1, 1]
            super().__init__(**kwargs)

    def __init__(self, network):
        self.network = network
        self.list_adapter = None
        self.list_view = None
        self.data = None
        super().__init__()

    def on_pre_enter(self, *args):
        members = list(self.network.hashgraph.known_members.values())
        members.sort(key=lambda x: x.formatted_name)
        self.data = [{'member': m, 'is_selected': False} for m in members if m != self.network.me]

        def args_converter(row_index, rec):
            return {
                'text': rec['member'].formatted_name,
                'height': 40
            }

        list_adapter = ListAdapter(data=self.data,
                                   args_converter=args_converter,
                                   cls=self.MemberListItemButton,
                                   selection_mode='single',
                                   propagate_selection_to_data=True,
                                   allow_empty_selection=True)

        def selection_change_callback(adapter):
            if len(adapter.selection) == 1:
                self.ids.send_button.disabled = False

        list_adapter.bind(on_selection_change=selection_change_callback)

        self.list_view = ListView(adapter=list_adapter, size_hint_x=0.8)

        self.ids.receiver_layout.add_widget(self.list_view)

    def on_leave(self, *args):
        self.ids.comment_field.text = ''
        self.ids.amount_field.text = ''
        self.ids.receiver_layout.remove_widget(self.list_view)

    def send_transaction(self):
        try:
            amount = int(self.ids.amount_field.text)
            comment = self.ids.comment_field.text
            receiver = next(x['member'] for x in self.data if x['is_selected'])

            bptc.logger.info("Transfering {} BPTC to {} with comment '{}'".format(amount, receiver, comment))

            self.network.send_transaction(amount, comment, receiver)
        except ValueError:
            print("Error parsing values")


class TransactionsScreen(KivyScreen):
    """Transaction screen of the Kivy App"""

    def __init__(self, network):
        self.network = network
        self.list_view = None
        super().__init__()

    def on_pre_enter(self, *args):
        # Load relevant transactions
        transactions = self.network.hashgraph.get_relevant_transactions()
        # Create updated list

        def args_converter(row_index, rec):
            return {
                'height': 60,
                'markup': True,
                'halign': 'center',
                'text': rec['formatted']
            }

        list_adapter = SimpleListAdapter(data=transactions,
                                         args_converter=args_converter,
                                         cls=Label)

        self.list_view = ListView(adapter=list_adapter, size_hint_y=8)

        self.ids.box_layout.add_widget(self.list_view, index=1)

    def on_leave(self, *args):
        self.ids.box_layout.remove_widget(self.list_view)


class MembersScreen(KivyScreen):
    """Members screen of the Kivy App"""

    def __init__(self, network):
        self.network = network
        self.list_view = None
        super().__init__()

    def on_pre_enter(self, *args):
        members = self.network.hashgraph.known_members.values()
        members = [m for m in members if m != self.network.me]
        members.sort(key=lambda x: x.formatted_name)
        # Create updated list

        def args_converter(row_index, rec):
            return {
                'height': 60,
                'markup': True,
                'halign': 'center',
                'text': repr(members[row_index]),
            }

        list_adapter = SimpleListAdapter(data=members,
                                         args_converter=args_converter,
                                         cls=Label)

        self.list_view = ListView(adapter=list_adapter, size_hint_y=8)

        self.ids.box_layout.add_widget(self.list_view, index=1)

    def on_leave(self, *args):
        self.ids.box_layout.remove_widget(self.list_view)


class PublishNameScreen(KivyScreen):
    """PublishName screen of the Kivy App."""

    def __init__(self, network):
        self.network = network
        super().__init__()

    def publish_name(self):
        name = self.ids.name_field.text
        self.network.publish_name(name)


class DebugScreen(KivyScreen):
    """Debug screen of the Kivy App."""
    def __init__(self, network, defaults, app):
        self.network = network
        self.defaults = defaults
        self.pushing = False
        self.app = app
        super().__init__()

        # endless loop for updating information displayed
        def update_statistics():
            self.ids.listening_interface_label.text = 'Listening interface: {}:{}'.format(bptc.ip, bptc.port)
            self.ids.event_count_label.text = '{} events, {} confirmed'.format(len(self.hashgraph.lookup_table.keys()),
                                                                               len(self.hashgraph.ordered_events))
            self.ids.last_push_sent_label.text = 'Last push sent: {}'.format(self.network.last_push_sent)
            self.ids.last_push_received_label.text = 'Last push received: {}'.format(self.network.last_push_received)

            t = threading.Timer(1, update_statistics)
            t.daemon = True
            t.start()

        update_statistics()

    @property
    def hashgraph(self):
        return self.network.hashgraph

    @property
    def me(self):
        return self.network.me

    # Get value for an attribute from its input element
    def get(self, key):
        for id_, obj in self.ids.items():
            if id_ == key:
                return obj.text
        return self.defaults[key]

    # --------------------------------------------------------------------------
    # DebugScreen actions
    # --------------------------------------------------------------------------

    @staticmethod
    def change_log_level():
        """Toggle the log level."""
        bptc.toggle_stdout_log_level()
        print('Toggled stdout log level. New level: {}'.format(bptc.get_stdout_levelname()))

    def confirm_reset_popup(self):
        """Ask for confirmation to do member-reset."""
        from .confirmpopup import ConfirmPopup
        popup = ConfirmPopup(text='Reset database containing the local hashgraph')
        popup.bind(on_ok=self.do_reset)
        popup.open()

    def do_reset(self, _dialog):
        """Perform a member-reset"""
        bptc.logger.warn('Deleting local database containing the hashgraph')
        self.network.reset()
        self.defaults['member_id'] = self.me.formatted_name

    def register(self):
        """Register at the given registry address."""
        ip, port = self.get('registering_address').split(':')
        network_utils.register(self.me.id, self.get('listening_port'), ip, port)

    def query_members(self):
        """Query members from the given registry address"""
        ip, port = self.get('query_members_address').split(':')
        network_utils.query_members(self, ip, port)

    def push(self):
        """Push events to the given member address."""
        ip, port = self.get('push_address').split(':')
        self.network.push_to(ip, int(port))

    def push_random(self):
        """Push to a random member."""
        if not self.pushing:
            self.network.start_push_thread()
            self.pushing = True
        else:
            self.network.stop_push_thread()
            self.pushing = False
