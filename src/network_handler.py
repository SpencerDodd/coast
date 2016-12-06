import os
import unittest
import requests
from torrent import Torrent
from auxillarymethods import one_directory_back
"""
This is a handler for network requests and responses between the client,
trackers, and peers.
"""

class NetworkHandler:
	def __init__(self):
		self._active_torrents = []

	"""
	Adds a torrent to the network handler
	"""
	def add_torrent(self, torrent_to_add):
		self._active_torrents.append(torrent_to_add)


	"""
	Performs a request for a torrent
	"""
	def send_requests_if_possible(self):
		for active_torrent in self._active_torrents:
			if active_torrent.can_request():
				self.send_request(active_torrent)


	"""
	Sends the torrent's request and feeds the response back to the torrent
	for processing.
	"""
	def send_request(self, requestable_torrent):
		torrent_request = requestable_torrent.get_tracker_request()
		response = requests.get(torrent_request)
		requestable_torrent.process_tracker_response(response)


class NetworkHanderTests(unittest.TestCase):
	def test_request_formatting(self):
		test_torrent = Torrent()
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test_data/")
		test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent.initialize_metadata_from_file(os.path.join(test_data_directory,test_torrent_file))

		peer_id = "-Co0001-7a673c102d185bdbd3d1691cc66d3c36"
		port = 6881
		test_torrent.intialize_for_tracker_requests(peer_id, port)

		test_handler = NetworkHandler()
		test_handler.add_torrent(test_torrent)
		test_handler.send_requests_if_possible()
		print (test_torrent.get_last_response().text)

if __name__ == "__main__":
	unittest.main()
















