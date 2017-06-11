from .client import Client
from .bptc_wallet import BPTCWallet

from kivy.config import Config
# size of an iPhone 6 Plus
Config.set('graphics', 'width', '414')
Config.set('graphics', 'height', '736')


class Mobile(Client):
    pass

class MobileApp(BPTCWallet):
    def build(self):
        return Mobile(self.network)

if __name__ == '__main__':
    MobileApp().run()
