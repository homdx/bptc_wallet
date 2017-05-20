from kivy.uix.button import Button
from functools import partial
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.lang import Builder
import threading
import time
from member import Member
from log_helper import *


# https://github.com/kivy/kivy/wiki/Working-with-Python-threads-inside-a-Kivy-application
class Core(GridLayout):

    def __init__(self):
        Builder.load_file('client_layout.kv')
        super().__init__()
        self.stop = threading.Event()
        self.add_widget(Button(text='Button 1', on_press=partial(self.start_loop_thread)))
        self.member = Member.create()

    def start_loop_thread(self, *args):
        logger.info("Starting event loop...")
        threading.Thread(target=self.loop).start()

    def loop(self):
        iteration = 0
        while True:
            if self.stop.is_set():
                # Stop running this thread so the main Python process can exit.
                return
            iteration += 1
            logger.info('#{}'.format(iteration))
            self.member.heartbeat()
            time.sleep(1)


class HPTClient(App):

    def __init__(self):
        super().__init__()

    def on_stop(self):
        # The Kivy event loop is about to stop, set a stop signal;
        # otherwise the app window will close, but the Python process will
        # keep running until all secondary threads exit.
        logger.info("Stopping...")
        self.root.stop.set()

    def build(self):
        return Core()


if __name__ == '__main__':
    HPTClient().run()
