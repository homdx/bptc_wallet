import threading
import time
from functools import partial

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.button import Button, Label
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout

from hashgraph.member import Member
from networking.protocol import *
from twisted.internet import threads, reactor

import argparse

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
        self.stop = threading.Event()
        self.listening_port_input = TextInput(text='8000')
        self.add_widget(self.listening_port_input)
        self.add_widget(Button(text='start reactor', on_press=partial(self.start_reactor_thread)))
        self.connect_to_ip_input = TextInput(text='localhost')
        self.add_widget(self.connect_to_ip_input)
        self.connect_to_port_input = TextInput(text='8000')
        self.add_widget(self.connect_to_port_input)
        self.add_widget(Button(text='connect to', on_press=partial(self.start_loop_thread)))
        self.member = Member.create()

    def start_loop_thread(self, *args):
        logger.info("Starting event loop...")
        threading.Thread(target=self.loop).start()

    def single_step(self, *args):
        logger.info("Stepping...")
        threading.Thread(target=self.step).start()

    def loop(self):
        iteration = 0
        while True:
            if self.stop.is_set():
                # Stop running this thread so the main Python process can exit.
                return
            iteration += 1
            logger.info('#{}'.format(iteration))
            self.step()
            time.sleep(2)

    def step(self):
        self.member.heartbeat()
        self.member.sync(self.connect_to_ip_input.text, int(self.connect_to_port_input.text))  # DEV: this is intended to sync with the other member

    def start_reactor_thread(self, *args):
        threading.Thread(target=self.start_reactor).start()

    def start_reactor(self):
        port = int(self.listening_port_input.text)
        logger.info("Listening on port {}".format(port))
        factory = protocol.ServerFactory()
        factory.protocol = EchoServer
        reactor.listenTCP(port, factory)
        reactor.run(installSignalHandlers=0)


class HPTWallet(App):

    def __init__(self, args):
        super().__init__()
        self.args = args

    def on_stop(self):
        # The Kivy event loop is about to stop, set a stop signal;
        # otherwise the app window will close, but the Python process will
        # keep running until all secondary threads exit.
        logger.info("Stopping...")
        reactor.callFromThread(reactor.stop)  # threads.blockingCallFromThread(reactor, ...)?
        self.root.stop.set()

    def build(self):
        return Core(self.args)


def main():
    #parser = argparse.ArgumentParser(description='HPT Wallet')
    #parser.add_argument('--id', type=int, help='command line id for dev')
    #args = parser.parse_args()
    args = ()
    HPTWallet(args).run()

if __name__ == '__main__':
    main()
