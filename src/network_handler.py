import unittest
from torrent import Torrent
"""
This is a handler for network requests and responses between the client,
trackers, and peers.
"""

class NetworkHandler:
	def __init__(self):
		self._active_torrents = []

	"""
	Performs a request for a torrent
	"""
	def send_requests_if_possible(self):
		for active_torrent in self._active_torrents:
			if active_torrent.can_request():
				self.send_request(active_torrent)

	"""
	Sends the torrent's request
	"""
	def send_request(self, requestable_torrent):
		torrent_request = requestable_torrent.get_tracker_request()
		print (torrent_request)

class NetworkHanderTests(unittest.TestCase):
	def test_network_handler(self):
		self.assertEquals(1, 1)

if __name__ == "__main__":
	unittest.main()