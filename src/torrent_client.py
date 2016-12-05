import unittest
from torrent import Torrent

"""
This is the main torrent client file.
"""
class Client:
	def __init__(self):
		"""
		Dictionary of active torrents. Key value is the name 
		"""
		self.active_torrents = {}

class TestClient(unittest.TestCase):
	def test_something(self):
		self.assertEquals(1, 1)

if __name__ == "__main__":
	unittest.main()