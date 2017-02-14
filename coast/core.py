import os
import sys
import hashlib
import tkFileDialog
from Tkinter import Tk, Frame
import socket
from constants import CLIENT_ID_STRING, CURRENT_VERSION
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
		user_port = input("Please enter a port to run coast on (Standard: 6881-6889): ")
		return user_port

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

	# TODO
	'''
	We need to start handling torrents here including handling for tracker requests / re-announces for updated peer
	lists, and final file compilation from downloaded parts
	'''
	def run(self):
		while True:
			for torrent in self._active_torrents:
				torrent.main_control_loop()


def main():
	root = Tk()
	root.withdraw()
	test_core = Core(root)
	test_core.add_torrent_from_browser()
	test_core.run()

if __name__ == "__main__":
	main()
