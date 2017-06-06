from kivy.app import App
from .client import Client


class Desktop(Client):
    pass

class DesktopApp(App):
    def build(self):
        return Desktop()

if __name__ == '__main__':
    DesktopApp().run()
