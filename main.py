import threading
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout
from hashgraph.member import Member
from networking.push_protocol import PushServerFactory
from networking.pull_protocol import PullServerFactory
from twisted.internet import reactor
from utilities.log_helper import logger
from kivy.config import Config
Config.set('graphics', 'width', '600')
Config.set('graphics', 'height', '50')

import gi
gi.require_version('Gtk', '3.0')


# https://github.com/kivy/kivy/wiki/Working-with-Python-threads-inside-a-Kivy-application
class Core(GridLayout):

    def __init__(self, args):
        self.args = args
        Builder.load_file('wallet_layout.kv')
        super().__init__()
        self.member = Member.create()
        self.stop = threading.Event()
        self.listening_port_input = TextInput(text='8000')
        self.add_widget(self.listening_port_input)
        self.add_widget(Button(text='start listening', on_press=self.start_listening))
        self.connect_to_ip_input = TextInput(text='localhost')
        self.add_widget(self.connect_to_ip_input)
        self.connect_to_port_input = TextInput(text='8000')
        self.add_widget(self.connect_to_port_input)
        self.add_widget(Button(text='sync with', on_press=self.sync))
        self.add_widget(Button(text='heartbeat', on_press=self.heartbeat))

    # def start_loop_thread(self, *args):
    #     def loop():
    #         iteration = 0
    #         while True:
    #             if self.stop.is_set():
    #                 # Stop running this thread so the main Python process can exit.
    #                 return
    #             iteration += 1
    #             logger.info('#{}'.format(iteration))
    #             self.step()
    #             time.sleep(2)
    #
    #     logger.info("Starting event loop...")
    #     threading.Thread(target=loop).start()

    def heartbeat(self, *args):
        self.member.heartbeat()

    def sync(self, *args):
        self.member.push_to(self.connect_to_ip_input.text, int(self.connect_to_port_input.text))

    def start_listening(self, *args):
        port = int(self.listening_port_input.text)
        logger.info("Push server listens on port {}...".format(port))
        factory1 = PushServerFactory(self.member.received_data_callback)
        reactor.listenTCP(port, factory1)
        logger.info("Pull server listens on port {}...".format(port + 1))
        factory2 = PullServerFactory(self.member)
        reactor.listenTCP(port + 1, factory2)


class HPTWallet(App):

    def __init__(self, args):
        super().__init__()
        self.args = args
        self.start_reactor_thread()

    @staticmethod
    def start_reactor_thread():
        def start_reactor():
            reactor.run(installSignalHandlers=0)

        threading.Thread(target=start_reactor).start()

    def on_stop(self):
        # The Kivy event loop is about to stop, set a stop signal;
        # otherwise the app window will close, but the Python process will
        # keep running until all secondary threads exit.
        logger.info("Stopping...")
        reactor.callFromThread(reactor.stop)
        self.root.stop.set()

    def build(self):
        self.title = 'HPT Wallet'
        return Core(self.args)


def main():
    #parser = argparse.ArgumentParser(description='HPT Wallet')
    #parser.add_argument('--id', type=int, help='command line id for dev')
    #args = parser.parse_args()
    args = ()
    HPTWallet(args).run()

if __name__ == '__main__':
    main()
