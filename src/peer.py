import unittest
"""
This class represents a peer
"""

class Peer:
	def __init__(self):
		self.byte_string_chunk = None
		self.ip = ""
		self.port = None

	def initialize_with_chunk(self, byte_string_chunk):
		self.byte_string_chunk = byte_string_chunk
		ip_chunk = byte_string_chunk[:4]
		port_chunk = byte_string_chunk[4:]

		for index,char in enumerate(ip_chunk):
			if index != 3:
				self.ip += str(ord(char)) + "."
			else:
				self.ip += str(ord(char))

		self.port = ord(port_chunk[0]) * 256 + ord(port_chunk[1])


	# -------------------------------------------------------------------------
	# Getters
	def get_ip(self):
		return self.ip

	def get_port(self):
		return self.port
	# -------------------------------------------------------------------------

"""
Tests
"""

class TestPeer(unittest.TestCase):
	def test_initialization(self):
		test_peer_chunk = u"N\xe6\xcd2\xc5D"
		test_peer = Peer()
		test_peer.initialize_with_chunk(test_peer_chunk)
		expected_peer_ip = "78.230.205.50"
		expected_peer_port = 50500
		self.assertEqual(expected_peer_ip, test_peer.get_ip())
		self.assertEqual(expected_peer_port, test_peer.get_port())


if __name__ == "__main__":
	unittest.main()