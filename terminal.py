import urwid
from shutil import get_terminal_size
import asyncio

HISTORY_MAX = 512 # Maximum number of lines to save (used with scrolling)

class Terminal(urwid.WidgetWrap):
	def __init__(self):
		self.header = urwid.Text("DiscordCLI", align="center")
		self._header_map = urwid.AttrMap(self.header, "secondary")

		self._div_map = urwid.AttrMap(urwid.Divider(), "primary")

		self.history = []
		self.history_ptr = 0
		self.body = urwid.Text("")
		body_container = urwid.ListBox([self.body])
		self._body_map = urwid.AttrMap(body_container, "primary")

		self.status = urwid.Text("")

		self.input_buffer = ""
		self.buffer_set = False
		self.chatbox = urwid.Edit("Logging in...", "")

		footer = urwid.Pile([self.status, self.chatbox])
		self._footer_map = urwid.AttrMap(footer, "secondary")

		self.typing_callback = lambda key: None

		self._w = urwid.Frame(
			header=urwid.Pile([self._header_map, self._div_map]),
			body=self._body_map,
			footer=self._footer_map,
			focus_part="footer"
		)

	def _draw_history(self):
		dims = get_terminal_size()

		lines = []
		start = -(dims.lines - 4 + self.history_ptr)
		end = -self.history_ptr if self.history_ptr != 0 else len(self.history)
		for line in self.history[start:end]:
			lines.extend([
				line[i:(i + dims.columns)]
				for i in range(0, len(line), dims.columns)
			])

		self.body.set_text("\n".join(lines[-(dims.lines - 4):]))

	def print(self, output: str):
		# Append to history
		old_len = len(self.history)
		self.history.extend(output.split("\n"))
		if len(self.history) > HISTORY_MAX:
			self.history = self.history[-HISTORY_MAX:]
		new_len = len(self.history)

		# Update pointer
		if new_len > old_len and self.history_ptr != 0:
			self.history_ptr += new_len - old_len

		# Draw
		self._draw_history()

	async def input(self) -> str:
		while not self.buffer_set:
			await asyncio.sleep(0.01)

		ret = self.input_buffer
		self.input_buffer = ""
		self.buffer_set = False
		return ret
	
	def set_title(self, title: str):
		self.header.set_text(title)

	def set_status(self, status: str):
		self.status.set_text(status)

	def set_prompt(self, prompt: str):
		self.chatbox.set_caption(prompt)

	def keypress(self, size, key):
		if key == "esc":
			raise urwid.ExitMainLoop()
		if key == "enter":
			self.input_buffer = self.chatbox.edit_text
			self.buffer_set = True
			self.chatbox.set_edit_text("")
			return
		if key == "up":
			if self.history_ptr < len(self.history) - (get_terminal_size().lines - 4):
				self.history_ptr += 1
				self._draw_history()
			return
		if key == "down":
			if self.history_ptr > 0:
				self.history_ptr -= 1
				self._draw_history()
			return

		if key == "insert":
			self.chatbox.insert_text("\n")
		if key != "backspace": self.typing_callback(key)

		super(Terminal, self).keypress(size, key)

	def mouse_event(self, size, event, button, col, row, focus):
		pass
