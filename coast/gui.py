from Tkinter import Tk, Text, TOP, BOTH, X, Y, N, S, E, W, LEFT, RIGHT, BOTTOM, \
	Listbox, IntVar, Scrollbar, VERTICAL, StringVar, Frame


class GUI(Frame):
	def __init__(self, parent, core):
		Frame.__init__(self, parent)

		self.core = core

	def initUI(self):
		self.parent.title("Coast Torrent Client")
		self.pack(fill=BOTH, expand=True)
