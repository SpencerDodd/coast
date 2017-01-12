import unittest
from bitarray import bitarray

from coast.peer import Peer
from test.test_data import test_bitfield


class TestPeer(unittest.TestCase):
	def test_initialization(self):
		test_peer_chunk = u"N\xe6\xcd2\xc5D"
		test_peer = Peer(test_peer_chunk)
		expected_peer_ip = "78.230.205.50"
		expected_peer_port = 50500
		self.assertEqual(expected_peer_ip, test_peer.ip)
		self.assertEqual(expected_peer_port, test_peer.port)

	def test_process_message(self):
		test_peer = Peer(u"N\xe6\xcd2\xc5D")

	def test_bitfield(self):
		test_peer_chunk = u"N\xe6\xcd2\xc5D"
		test_peer = Peer(test_peer_chunk)

		test_peer.process_bitfield(test_bitfield)
		self.assertEqual(test_peer.bitfield, bitarray("1"*(380*8)))