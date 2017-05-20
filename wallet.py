import threading
import time
from functools import partial

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout

from hashgraph.member import Member
from utils.log_helper import *
from network.network import *

import argparse

from kivy.config import Config
Config.set('graphics', 'width', '200')
Config.set('graphics', 'height', '50')


# https://github.com/kivy/kivy/wiki/Working-with-Python-threads-inside-a-Kivy-application
class Core(GridLayout):

    def __init__(self, args):
        self.args = args
        Builder.load_file('wallet_layout.kv')
        super().__init__()
        self.stop = threading.Event()
        self.add_widget(Button(text='run', on_press=partial(self.start_loop_thread)))
        self.member = Member.create()

    def start_loop_thread(self, *args):
        logger.info("Starting event loop...")
        threading.Thread(target=self.step).start()
        # threading.Thread(target=self.loop).start()  # for loop

    def loop(self):
        iteration = 0
        while True:
            if self.stop.is_set():
                # Stop running this thread so the main Python process can exit.
                return
            iteration += 1
            logger.info('#{}'.format(iteration))
            self.step()
            time.sleep(1)

    def step(self):
        if self.args.id == 1:
            self.member.wait_for_sync_request()
        elif self.args.id == 2:
            self.member.heartbeat()
            self.member.sync()  # DEV: this is intended to sync with the other member


class HPTWallet(App):

    def __init__(self, args):
        super().__init__()
        self.args = args
        threading.Thread(target=self.start_server).start()

    def start_server(self):
        port = 8000 + int(self.args.id)
        logger.info("Listening on port {}".format(port))
        factory = protocol.ServerFactory()
        factory.protocol = Echo
        reactor.listenTCP(port, factory)
        reactor.run(installSignalHandlers=0)

    def on_stop(self):
        # The Kivy event loop is about to stop, set a stop signal;
        # otherwise the app window will close, but the Python process will
        # keep running until all secondary threads exit.
        logger.info("Stopping...")
        reactor.callFromThread(reactor.stop)
        self.root.stop.set()

    def build(self):
        return Core(self.args)


def main():
    parser = argparse.ArgumentParser(description='HPT Wallet')
    parser.add_argument('--id', type=int, help='command line id for dev')
    args = parser.parse_args()
    HPTWallet(args).run()

if __name__ == '__main__':
    main()
