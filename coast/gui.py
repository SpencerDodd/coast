from Tkinter import Tk, Text, TOP, BOTH, X, Y, N, S, E, W, LEFT, RIGHT, BOTTOM, \
	Listbox, IntVar, Scrollbar, VERTICAL, StringVar, Toplevel
from ttk import Frame, Label, Entry, Button, Progressbar
import tkFileDialog

from coast.constants import NEW_WINDOW_X, NEW_WINDOW_Y

from coast.torrent import Torrent


class GUI(Frame):
	def __init__(self, parent, core):
		Frame.__init__(self, parent)

		self.parent = parent
		self.core = core
		self.new_magnet_link = ""
		self.new_torrent_file_path = ""
		self.percent_complete = StringVar(self)

		self.initUI()

	def initUI(self):
		self.percent_complete.set(0)

		self.parent.title("Coast Torrent Client")
		self.pack(fill=BOTH, expand=True)

		self.add_torrent_input()
		self.add_torrent_list()
		self.add_progress_frame()

		self.update_progress()

	def add_torrent_input(self):

		input_frame = Frame(self)
		input_frame.pack(fill=Y)

		torrent_input_button = Button(input_frame, text="Add Torrent", command=self.add_torrent_callback)
		torrent_input_button.pack(side=TOP, anchor=E, padx=5, pady=5)

	def add_torrent_list(self):
		"""
		Adds a selectable list of active torrents to the UI. This allows us to change the actively-viewed torrent.
		"""
		list_frame = Frame(self)
		list_frame.pack(fill=X)

		list_label = Label(list_frame, text="Torrents", width=14)
		list_label.pack(side=LEFT, anchor=N, padx=5, pady=5)

		listbox = Listbox(list_frame, width=14, selectmode="single")
		listbox.pack(side=LEFT, padx=5, pady=5)
		for torrent in self.core.active_torrents:
			listbox.insert("end", torrent.torrent_name)
		list_browser = Button(list_frame, text="View Torrent", command=lambda listbox=listbox: self.view_torrent_callback(
								listbox.curselection()))
		list_browser.pack(side=RIGHT, anchor=E, padx=5, pady=5)

	def add_progress_frame(self):
		progress_frame = Frame(self)
		progress_frame.pack(fill=X, expand=True)

		total_progress_bar = Progressbar(progress_frame, orient='horizontal', mode='determinate')
		total_progress_bar['variable'] = self.percent_complete
		total_progress_bar.pack(expand=True, fill=BOTH, side=TOP)

		percent_complete_sign = Label(progress_frame, text="%", width=2)
		percent_complete_sign.pack(side=RIGHT, padx=5, pady=5)
		percent_complete_label = Label(progress_frame, textvariable=self.percent_complete, width=8)
		percent_complete_label.pack(side=RIGHT, padx=5, pady=5)

	def refresh_window(self):
		self.destroy_all_widgets()
		self.initUI()

	def destroy_all_widgets(self):
		for widget in self.winfo_children():
			widget.destroy()

	def view_torrent_callback(self, new_display_torrent_index):
		self.core.displayed_torrent = new_display_torrent_index
		self.refresh_window()

	def update_progress(self):
		if len(self.core.active_torrents) > 0:
			self.percent_complete.set(self.core.active_torrents[self.core.displayed_torrent].get_progress())
			self.after(50, self.update_progress)
		else:
			self.percent_complete.set(0)
			self.after(50, self.update_progress)

	def get_torrent_file(self):
		torrent_file_path = tkFileDialog.askopenfilename(parent=self, initialdir=self.core.download_dir, title="Select torrent file to download")
		self.new_torrent_file_path = torrent_file_path
		self.add_torrent()
		self.refresh_window()

	def add_torrent(self):
		if len(self.new_magnet_link) > 0:
			pass
		if len(self.new_torrent_file_path) > 0:
			new_torrent = Torrent(self.core._peer_id, self.core._coast_port, self.new_torrent_file_path)
			self.core.active_torrents.append(new_torrent)

		self.core.run()

	def add_torrent_callback(self):
		add_torrent_window = Toplevel(self)
		add_torrent_window.geometry("500x100+{}+{}".format(NEW_WINDOW_X, NEW_WINDOW_Y))
		add_torrent_label = Label(add_torrent_window, text="Add Torrent")
		add_torrent_label.pack(side="top", fill="both", expand=True, padx=5, pady=5)

		"""
		magnet_entry = Entry(add_torrent_window)
		magnet_entry.pack(fill=X, side=LEFT, anchor=W, padx=5, expand=True)
		magnet_entry.delete(0, "end")
		magnet_entry.insert(0, self.new_magnet_link)
		"""

		torrent_entry = Entry(add_torrent_window)
		torrent_entry.pack(fill=X, side=LEFT, anchor=W, padx=5, expand=True)
		torrent_entry.delete(0, "end")
		torrent_entry.insert(0, self.new_torrent_file_path)

		torrent_file_selection_button = Button(add_torrent_window, text="From File", command=self.get_torrent_file)
		torrent_file_selection_button.pack(fill=X, side=LEFT, anchor=W, padx=5, pady=5)

		add_torrent_button = Button(add_torrent_window, text="Add Torrent",command=self.add_torrent)
		add_torrent_button.pack(side="bottom")

