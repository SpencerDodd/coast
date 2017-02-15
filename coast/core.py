from __future__ import print_function
import os
import sys
import getopt
import hashlib
import tkFileDialog
from Tkinter import Tk, Frame
import threading
from constants import CLIENT_ID_STRING, CURRENT_VERSION, DEBUG, RUNNING_PORT, ARGUMENT_PARSING_ERROR_MESSAGE,\
	ACTIVITY_COMPLETED, ACTIVITY_INITIALIZE_CONTINUE, ACTIVITY_INITIALIZE_NEW, ACTIVITY_DOWNLOADING, ACTIVITY_STOPPED,\
	NEW_WINDOW_X, NEW_WINDOW_Y

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from coast.torrent import Torrent
from coast.gui import GUI
from coast.constants import LISTENING_PORT_MIN
from coast.constants import LISTENING_PORT_MAX

"""
This is the core of the torrent client.
"""


class Core:
	def __init__(self):
		"""
		Dictionary of active torrents
		
		Key value is the name of the torrent file
		Value is a Torrent object
		"""
		self.active_torrents = []
		self._peer_id = self.generate_peer_id()
		self._coast_port = self.get_open_port()
		self.download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
		self.run_thread = None

		self.displayed_torrent = 0

	def get_open_port(self):
		"""
		Gets an open port to run coast on.

		:return: port to run on
		scan_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		for scan_port in range(LISTENING_PORT_MIN, LISTENING_PORT_MAX):
			print ("Checking for open socket on port {}".format(scan_port))
			result = scan_socket.connect_ex(('127.0.0.1', scan_port))
			if result == 0:
				print ("Binding core to port {}".format(scan_port))
				return scan_port
			else:
				print ("Port {} already has process running".format(scan_port))

		# ask for another port if none are open
		"""
		if not RUNNING_PORT:
			user_port = input("Please enter a port to run coast on (Standard: 6881-6889): ")
			return user_port

		else:
			return RUNNING_PORT

	def generate_peer_id(self):
		"""
		Outputs a unique 20-byte urlencoded string used as the client identifier
		Uses Azureus-style encoding:
			'-' + (2-char client ID ascii) + (4-char integer version number) + '-'
		"""
		seed_string = "{}{}{}".format(os.getpgid(0), os.getcwd(), sys.platform)
		pre_versioned_peer_id = hashlib.sha1(seed_string).hexdigest()
		peer_id_sub = pre_versioned_peer_id[28:]
		
		peer_id = "-{}{}-{}".format(CLIENT_ID_STRING,CURRENT_VERSION,peer_id_sub)
		# DEBUG
		# print ("Generated Peer ID: {}".format(peer_id))
		return peer_id

	def add_torrent_from_browser(self):
		""" Adds a torrent to the core. Add with a magnet link, or from a file"""

		torrent_file_path = tkFileDialog.askopenfilename(parent=self, initialdir=self.download_dir, title="Select torrent file to download")
		new_torrent = Torrent(self._peer_id, self._coast_port, torrent_file_path)
		# DEBUG
		print ("Adding torrent to core: {}".format(new_torrent.torrent_name))
		self.active_torrents.append(new_torrent)

	# TODO
	def add_torrent_from_magnet(self):
		pass

	def control_torrents(self):
		for torrent in self.active_torrents:
			if torrent.activity_status == ACTIVITY_COMPLETED:
				sys.stdout.flush()
				print (torrent.get_status(display_status=False))
				torrent.compile_file_from_pieces(preserve_tmp=DEBUG)
				torrent.stop_torrent()

			if torrent.activity_status == ACTIVITY_INITIALIZE_NEW or ACTIVITY_INITIALIZE_CONTINUE:
				if not torrent.tracker_request_sent:
					torrent.start_torrent()

			if torrent.activity_status == ACTIVITY_DOWNLOADING:
				torrent.update_completion_status()
				# torrent.reannounce_if_possible

			if torrent.activity_status == ACTIVITY_STOPPED:
				print ("Torrent is stopped")

	def update_displayed_torrent(self, index):
		self.displayed_torrent = index

	def show_display(self):
		display_torrent = self.active_torrents[self.displayed_torrent]
		print (display_torrent.get_status(display_status=False))
	'''
	We need to start a threaded handler for the active torrents. This way we can control program flow and torrent
	status without being blocked by Twisted event handling.
	'''
	def run_cmd(self):
		print ("Running the core.")
		torrent_file_path = raw_input("Please enter the filepath of the .torrent file you would like to download: ")
		new_torrent = Torrent(self._peer_id, self._coast_port, str(torrent_file_path))
		# DEBUG
		print ("Adding torrent to core: {}".format(new_torrent.torrent_name))
		self.active_torrents.append(new_torrent)
		self.run()
		while True:
			self.show_display()

	def run_gui(self):
		root = Tk()
		root.geometry("700x570+{}+{}".format(NEW_WINDOW_X, NEW_WINDOW_Y))
		#root.attributes("-topmost", True)
		gui = GUI(root, self)
		gui.mainloop()

	def run(self):
		self.run_thread = threading.Thread(target=self.control_torrents)
		self.run_thread.start()


def main(argv):
	run_core = Core()
	try:
		opts, args = getopt.getopt(argv,"hm:",["mode="])
	except getopt.GetoptError:
		print ("Parsing Error")
		print (ARGUMENT_PARSING_ERROR_MESSAGE)
		sys.exit(2)
	if len(argv) < 1:
		print ("Please enter a runmode argument")
		print (ARGUMENT_PARSING_ERROR_MESSAGE)
	for opt, arg in opts:
		if opt == '-h':
			print ("Usage:")
			print (ARGUMENT_PARSING_ERROR_MESSAGE)
			sys.exit()
		elif opt in ("-m", "--mode"):
			if arg == "cmd":
				run_core.run_cmd()
			if arg == "gui":
				run_core.run_gui()
			else:
				print ("Invalid runmode")
				print (ARGUMENT_PARSING_ERROR_MESSAGE)
		else:
			print (ARGUMENT_PARSING_ERROR_MESSAGE)


if __name__ == "__main__":
	main(sys.argv[1:])
