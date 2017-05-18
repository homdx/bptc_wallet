from kivy.uix.button import Button
from functools import partial
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
import threading
import time
from node import Node
import logging


# https://github.com/kivy/kivy/wiki/Working-with-Python-threads-inside-a-Kivy-application
class Worker(GridLayout):

    def __init__(self):
        super().__init__()

        self.node = Node.create()

        button_1 = Button(text='Button 1', on_press=partial(self.start_loop_thread))
        self.add_widget(button_1)

    stop = threading.Event()

    def start_loop_thread(self, *args):
        logging.info("Starting...")
        threading.Thread(target=self.loop).start()

    def loop(self):
        iteration = 0
        while True:
            if self.stop.is_set():
                # Stop running this thread so the main Python process can exit.
                return
            iteration += 1
            logging.info('#{}'.format(iteration))
            self.node.heartbeat_callback()
            time.sleep(1)


class HPTClient(App):

    def __init__(self):
        super().__init__()

    def on_stop(self):
        # The Kivy event loop is about to stop, set a stop signal;
        # otherwise the app window will close, but the Python process will
        # keep running until all secondary threads exit.
        logging.info("Stopping...")
        self.root.stop.set()

    def build(self):
        return Worker()


if __name__ == '__main__':
    HPTClient().run()
