import kivy
from kivy.uix.screenmanager import Screen
from kivy.adapters.listadapter import ListAdapter
from kivy.adapters.simplelistadapter import SimpleListAdapter
from kivy.uix.listview import ListItemButton, ListView
from kivy.uix.label import Label
import bptc
import bptc.networking.utils as network_utils
from bptc.data.transaction import TransactionStatus, MoneyTransaction
import threading

kivy.require('1.0.7')


class MainScreen(Screen):
    def __init__(self, network, cl_args):
        self.defaults = {
            'listening_port': cl_args.port,
            'push_address': 'localhost:8000',
            'registering_address': 'localhost:9000',
            'query_members_address': 'localhost:9001',
            'member_id': 'Some-ID'
        }
        self.network = network
        self.hashgraph = network.hashgraph
        self.me = network.hashgraph.me
        self.defaults['member_id'] = self.me.formatted_name
        super().__init__()
        self.pushing = False

        def update_user_details():
            self.ids.account_balance_label.text = 'Account balance: {} BPTC'.format(self.me.account_balance)
            self.ids.account_name_label.text = '{} (Port: {})'.format(
                self.me.formatted_name,
                self.defaults['listening_port']
            )
            t = threading.Timer(1, update_user_details)
            t.daemon = True
            t.start()

        update_user_details()

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
    # MainScreen actions
    # --------------------------------------------------------------------------

    def start_listening(self):
        network_utils.start_listening(self.network, self.get('listening_port'))

    def register(self):
        ip, port = self.get('registering_address').split(':')
        network_utils.register(self.me.id, self.get('listening_port'), ip, port)

    def query_members(self):
        ip, port = self.get('query_members_address').split(':')
        network_utils.query_members(self, ip, port)

    def push(self):
        ip, port = self.get('push_address').split(':')
        self.network.push_to(ip, int(port))

    def push_random(self):
        if not self.pushing:
            self.network.start_background_pushes()
            self.pushing = True
        else:
            self.network.stop_background_pushes()
            self.pushing = False


class NewTransactionScreen(Screen):

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
        self.data = [{'member': m, 'is_selected': False} for m in members]

        args_converter = lambda row_index, rec: {
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


class TransactionsScreen(Screen):

    def __init__(self, network):
        self.network = network
        self.list_view = None
        super().__init__()

    def on_pre_enter(self, *args):
        # Load relevant transactions
        transactions = []
        events = list(self.network.hashgraph.lookup_table.values())
        for e in events:
            if e.data is not None:
                for t in e.data:
                    if isinstance(t, MoneyTransaction) and self.network.me.to_verifykey_string() in [e.verify_key, t.receiver]:
                        transactions.append({
                            'receiver': self.network.hashgraph.known_members[t.receiver].formatted_name if t.receiver in self.network.hashgraph.known_members else t.receiver,
                            'sender': self.network.hashgraph.known_members[e.verify_key].formatted_name if e.verify_key in self.network.hashgraph.known_members else e.verify_key,
                            'amount': t.amount,
                            'comment': t.comment,
                            'time': e.time,
                            'status': TransactionStatus.text_for_value(t.status),
                            'is_received': t.receiver == self.network.hashgraph.me.to_verifykey_string()
                        })

        transactions.sort(key=lambda x: x['time'], reverse=True)

        # Create updated list
        args_converter = lambda row_index, rec: {
            'height': 60,
            'markup': True,
            'halign': 'center',
            'text': '{} [b]{} BPTC[/b] {} [b]{}[/b] ({})\n{}'.format(
                'Received' if rec['is_received'] else 'Sent',
                rec['amount'],
                'from' if rec['is_received'] else 'to',
                rec['sender'] if rec['is_received'] else rec['receiver'],
                rec['status'],
                '"{}"'.format(rec['comment']) if rec['comment'] is not None and len(rec['comment']) > 0 else ''
            )
        }

        list_adapter = SimpleListAdapter(data=transactions,
                                   args_converter=args_converter,
                                   cls=Label)

        self.list_view = ListView(adapter=list_adapter, size_hint_y=8)

        self.ids.box_layout.add_widget(self.list_view, index=1)

    def on_leave(self, *args):
        self.ids.box_layout.remove_widget(self.list_view)


class PublishNameScreen(Screen):

    def __init__(self, network):
        self.network = network
        super().__init__()

    def publish_name(self):
        name = self.ids.name_field.text
        self.network.publish_name(name)
