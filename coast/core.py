from __future__ import print_function
import os
import sys
import hashlib
import tkFileDialog
from Tkinter import Tk, Frame
import threading
from constants import CLIENT_ID_STRING, CURRENT_VERSION, DEBUG, RUNNING_PORT,\
	ACTIVITY_COMPLETED, ACTIVITY_INITIALIZE_CONTINUE, ACTIVITY_INITIALIZE_NEW, ACTIVITY_DOWNLOADING, ACTIVITY_STOPPED
from helpermethods import one_directory_back

from coast.torrent import Torrent
from coast.constants import LISTENING_PORT_MIN
from coast.constants import LISTENING_PORT_MAX

"""
This is the core of the torrent client.
"""


class Core(Frame):
	def __init__(self, parent):
		Frame.__init__(self, parent)
		"""
		Dictionary of active torrents
		
		Key value is the name of the torrent file
		Value is a Torrent object
		"""
		self._active_torrents = []
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
		print ("Generated Peer ID: {}".format(peer_id))
		return peer_id

	def add_torrent_from_browser(self):
		"""
		Adds a torrent to the core. Add with a magnet link, or from a file
		"""
		torrent_file_path = tkFileDialog.askopenfilename(parent=self, initialdir=self.download_dir, title="Select torrent file to download")
		new_torrent = Torrent(self._peer_id, self._coast_port, torrent_file_path)
		# DEBUG
		print ("Adding torrent to core: {}".format(new_torrent.torrent_name))
		self._active_torrents.append(new_torrent)

	# TODO
	def add_torrent_from_magnet(self):
		pass

	def control_torrents(self):

		display_torrent = self._active_torrents[self.displayed_torrent]
		if display_torrent.activity_status == ACTIVITY_COMPLETED:
			print (display_torrent.get_status(display_status=False))
			display_torrent.compile_file_from_pieces(preserve_tmp=DEBUG)
			display_torrent.stop_torrent()

		if display_torrent.activity_status == ACTIVITY_INITIALIZE_NEW or ACTIVITY_INITIALIZE_CONTINUE:
			if not display_torrent.tracker_request_sent:
				display_torrent.start_torrent()

		if display_torrent.activity_status == ACTIVITY_DOWNLOADING:
			display_torrent.update_completion_status()
			print (display_torrent.get_status(display_status=False))

			# torrent.reannounce_if_possible

		if display_torrent.activity_status == ACTIVITY_STOPPED:
			print ("Torrent is stopped")

	# TODO
	'''
	We need to start a threaded handler for the active torrents. This way we can control program flow and torrent
	status without being blocked by Twisted event handling.
	'''
	def run(self):
		print ("Running the core.")
		while True:
			self.run_thread = threading.Thread(target=self.control_torrents)
			self.run_thread.start()


def main():
	root = Tk()
	root.withdraw()
	test_core = Core(root)
	test_core.add_torrent_from_browser()
	test_core.run()

if __name__ == "__main__":
	main()
