import unittest
from helpermethods import convert_hex_to_int
from messages import Message, PieceMessage
from bitarray import bitarray
"""
This class represents a peer
"""


class Peer:
	def __init__(self, peer_chunk):
		self.ip = ""
		self.port = None
		self.peer_id = None
		self.byte_string_chunk = self.initialize_with_chunk(peer_chunk)
		self.bitfield = bitarray(endian="big")
		self.message_buffer = []

		# for interaction with Torrent object
		self.current_piece = None

		# our control
		self.am_choking = True
		self.am_interested = False

		# peer control
		self.peer_choking = True
		self.peer_interested = False

	def initialize_with_chunk(self, byte_string_chunk):
		"""
		Initializes the peer from the given byte-string chunk that is expected to come from the
		`peers` key of the tracker response.

		:param byte_string_chunk: byte-string containing peer info
		:return: byte-string for reference
		"""
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

	def status(self):
		"""
		Returns a string of the status of the peer including debug information such as messages
		received, bitfield, ip, port, id, etc
		:return: string
		"""
		status_string = "Status of peer <<||{}||>>".format(self.peer_id) + \
			"\n\tip: {}".format(self.ip) + \
			"\n\tport: {}".format(self.port) + \
			"\n\tbitfield: {}".format(self.bitfield) + \
			"\n\tmessages: {}".format("".join(a.debug_values() for a in self.message_buffer))

		return status_string

	def finished_with_piece(self):
		"""
		Returns true if the piece is done downloading
		:return: boolean
		"""
		return self.current_piece.is_complete()

	def get_next_piece(self, next_piece):
		"""
		Sets the current piece to the given next piece and returns the previous current piece
		to be saved to disk by the torrent.

		:param next_piece: Piece to be downloaded
		:return: Finished piece
		"""
		previous_piece = self.current_piece
		self.current_piece = next_piece
		return previous_piece

	def set_piece(self, piece):
		self.current_piece = piece

	def process_choke(self, message):
		self.message_buffer.append(message)
		print ("Choked by peer <||{}||>".format(self.peer_id))
		self.peer_choking = True

	def process_unchoke(self, message):
		self.message_buffer.append(message)
		print ("Unchoked by peer <||{}||>".format(self.peer_id))
		self.peer_choking = False

	def process_interested(self, message):
		self.message_buffer.append(message)
		print ("Peer <||{}||> is interested".format(self.peer_id))
		self.peer_interested = True

	def process_not_interested(self, message):
		self.message_buffer.append(message)
		print ("Peer <||{}||> is not interested".format(self.peer_id))
		self.peer_interested = False

	def process_have(self, message):
		self.message_buffer.append(message)
		piece = message.payload
		print ("Peer <||{}||> has piece {}".format(self.peer_id, piece))
		self.bitfield[convert_hex_to_int(message.payload)] = 1

	def process_bitfield(self, message):
		"""
		The bitfield is a byte representation of pieces. Each bit of each byte in the bitfield
		represents the peer's ability to produce that piece (index 0 based from the first bit).
		Bytes are big endian in the BitTorrent protocol.

		bitfield.get(index) == 0 -> peer does not have piece at index
		bitfield.get(index) == 1 -> peer has piece at index

		:param message: bitfield as byte-string
		"""
		# P.O.C for ubuntu-16.10-desktop-amd64.iso.torrent
		# 60800 piece bytes / (20 bytes / piece) = 3040 pieces
		# 3040 pieces / 8 bits per byte  = 380
		# length of bitfield = 380
		# so each byte of the bitfield represents
		self.message_buffer.append(message)
		print ("Processing bitfield from peer <||{}||>".format(self.peer_id))
		self.bitfield.frombytes(message.payload)
		self.bitfield.tolist()

	def process_request(self, message):
		self.message_buffer.append(message)
		requested_piece = message.payload
		print ("Peer <||{}||> is requesting {}".format(self.peer_id, requested_piece))

	def process_piece(self, message):
		self.message_buffer.append(message)
		new_piece_message = PieceMessage(message.payload)
		print ("Peer <||{}||> sent piece index {} begin {}".format(self.peer_id,
																	new_piece_message.index,
																	new_piece_message.begin))
		self.current_piece.append_data(new_piece_message)

	def process_cancel(self, message):
		self.message_buffer.append(message)
		piece = message.payload
		print ("Peer <||{}||> has cancelled request for piece {}".format(self.peer_id, piece))

	def process_port(self, message):
		self.message_buffer.append(message)
		port = message.payload
		print ("Peer <||{}||> has sent port {}".format(self.peer_id, port))

	def process_extended_handshake(self, message):
		self.message_buffer.append(message)
		extension = message.payload
		print ("Peer <||{}||> has sent extension {}".format(self.peer_id, extension))


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
		self.assertEqual(expected_peer_port, test_peer.port)

	def test_process_message(self):
		test_peer = Peer(u"N\xe6\xcd2\xc5D")

	def test_bitfield(self):
		test_peer_chunk = u"N\xe6\xcd2\xc5D"
		test_peer = Peer(test_peer_chunk)
		test_bitfield = Message('\x00\x00\x01}\x05\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
								'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff '
								)
		test_peer.process_bitfield(test_bitfield)
		self.assertEqual(test_peer.bitfield, bitarray("1"*(380*8)))



if __name__ == "__main__":
	unittest.main()