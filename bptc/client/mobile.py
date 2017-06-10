from .client import Client
from kivy.app import App

from kivy.config import Config
# size of an iPhone 6 Plus
Config.set('graphics', 'width', '414')
Config.set('graphics', 'height', '736')


class Mobile(Client):
    pass


class MobileApp(App):
    def build(self):
        return Mobile()

if __name__ == '__main__':
    MobileApp().run()
