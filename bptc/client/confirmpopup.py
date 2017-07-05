from kivy.properties import StringProperty
from os.path import join, dirname
from kivy.lang import Builder
from kivy.uix.popup import Popup

Builder.load_file(join(dirname(__file__), 'confirmpopup.kv'))


class ConfirmPopup(Popup):
	text = StringProperty('')

	ok_text = StringProperty('OK')
	cancel_text = StringProperty('Cancel')

	__events__ = ('on_ok', 'on_cancel')

	def ok(self):
		self.dispatch('on_ok')
		self.dismiss()

	def cancel(self):
		self.dispatch('on_cancel')
		self.dismiss()

	def on_ok(self):
		pass

	def on_cancel(self):
		pass
