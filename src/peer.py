import unittest
"""
This class represents a peer
"""

class Peer:
	def __init__(self, peer_chunk):
		self.ip = ""
		self.port = None
		self.peer_id = None
		self.byte_string_chunk = self.initialize_with_chunk(peer_chunk)
		self.bitfield = None
		self.last_message = None
		self.message_buffer = []

		# our control
		self.am_choking = True
		self.am_interested = False

		# peer control
		self.peer_choking = True
		self.peer_interested = False


	def initialize_with_chunk(self, byte_string_chunk):
		self.byte_string_chunk = byte_string_chunk
		ip_chunk = byte_string_chunk[:4]
		port_chunk = byte_string_chunk[4:]

		for index, char in enumerate(ip_chunk):
			if index != 3:
				self.ip += str(ord(char)) + "."
			else:
				self.ip += str(ord(char))

		self.port = ord(port_chunk[0]) * 256 + ord(port_chunk[1])
		return byte_string_chunk

	def process_choke(self, message):
		print ("Choked by peer <||{}||>".format(self.peer_id))
		self.peer_choking = True

	def process_unchoke(self, message):
		print ("Unchoked by peer <||{}||>".format(self.peer_id))
		self.peer_choking = False

	def process_interested(self, message):
		print ("Peer <||{}||> is interested".format(self.peer_id))
		self.peer_interested = True

	def process_not_interested(self, message):
		print ("Peer <||{}||> is not interested".format(self.peer_id))
		self.peer_interested = False

	def process_have(self, message):
		piece = message.payload
		print ("Peer <||{}||> has piece {}".format(self.peer_id, piece))

	def process_bitfield(self, message):
		print ("Processing bitfield from peer <||{}||>".format(self.peer_id))

	def process_request(self, message):
		piece = message.payload
		print ("Peer <||{}||> is requesting {}".format(self.peer_id, piece))

	def process_piece(self, message):
		piece = message.payload
		print ("Peer <||{}||> sent piece {}".format(self.peer_id, piece))

	def process_cancel(self, message):
		piece = message.payload
		print ("Peer <||{}||> has cancelled request for piece {}".format(self.peer_id, piece))

	def process_port(self, message):
		port = message.payload
		print ("Peer <||{}||> has sent port {}".format(self.peer_id, port))

"""
Tests
"""

class TestPeer(unittest.TestCase):
	def test_initialization(self):
		test_peer_chunk = u"N\xe6\xcd2\xc5D"
		test_peer = Peer(test_peer_chunk)
		expected_peer_ip = "78.230.205.50"
		expected_peer_port = 50500
		self.assertEqual(expected_peer_ip, test_peer.ip)
		self.assertEqual(expected_peer_port, test_peer.port())

	def test_process_message(self):
		test_peer = Peer(u"N\xe6\xcd2\xc5D")



if __name__ == "__main__":
	unittest.main()