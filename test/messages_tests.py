import os
import unittest

from coast.helpermethods import convert_hex_to_int, convert_int_to_hex
from test.test_data import test_captured_request, test_stream_processor_stream, \
	test_piece_message, test_first_piece_message, test_captured_piece, test_torrent
from coast.piece import Piece
from coast.messages import HandshakeMessage, StreamProcessor, PieceMessage, RequestMessage
from coast.constants import REQUEST_SIZE


class MessageTests(unittest.TestCase):
	def test_client_handshake(self):
		test_info_hash = "\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z"
		test_peer_id = "-CO0001-5208360bf90d"
		test_handshake = HandshakeMessage(info_hash=test_info_hash, peer_id=test_peer_id)
		expected_handshake_string = "\x13BitTorrent protocol\x00\x00\x00\x00\x00\x00\x00" + \
			"\x00\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z-CO0001-5208360bf90d"
		self.assertEqual(expected_handshake_string, test_handshake.message())

	def test_peer_handshake(self):
		test_handshake_data = "\x13" + \
			"\x42\x69\x74\x54\x6f\x72\x72\x65\x6e\x74\x20\x70\x72\x6f\x74\x6f\x63\x6f\x6c" + \
			"\x00\x00\x00\x00\x00\x00\x00\x00" + \
			"\x04\x03\xfb\x47\x28\xbd\x78\x8f\xbc\xb6\x7e\x87\xd6\xfe\xb2\x41\xef\x38\xc7\x5a" + \
			"\x2d\x43\x4f\x30\x30\x30\x31\x2d\x35\x32\x30\x38\x33\x36\x30\x62\x66\x39\x30\x64"

		test_handshake = HandshakeMessage(data=test_handshake_data)
		expected_handshake_string = "\x13BitTorrent protocol\x00\x00\x00\x00\x00\x00\x00" + \
			"\x00\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z-CO0001-5208360bf90d"
		self.assertEqual(expected_handshake_string, test_handshake.message())

	def test_captured_peer_handshake(self):
		captured_handshake = "\x13\x42\x69\x74\x54\x6f\x72\x72\x65\x6e\x74\x20\x70\x72\x6f\x74" + \
							 "\x6f\x63\x6f\x6c\x00\x00\x00\x00\x00\x10\x00\x05\x04\x03\xfb\x47" + \
							 "\x28\xbd\x78\x8f\xbc\xb6\x7e\x87\xd6\xfe\xb2\x41\xef\x38\xc7\x5a" + \
							 "\x2d\x71\x42\x33\x33\x41\x30\x2d\x6f\x2d\x67\x30\x34\x79\x7a\x4f" + \
							 "\x28\x21\x2e\x6c"
		captured_handshake = HandshakeMessage(data=captured_handshake)
		expected_handshake_string = "\x13" + \
								"BitTorrent protocol" + \
								"\x00\x00\x00\x00\x00\x10\x00\x05" + \
								"\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z" + \
								"-qB33A0-o-g04yzO(!.l"

		self.assertEqual(expected_handshake_string, captured_handshake.message())

	def test_stream_processor(self):
		test_stream_processor = StreamProcessor(test_torrent.bitfield)
		test_stream_processor.parse_stream(test_stream_processor_stream)
		self.assertEqual(4, len(test_stream_processor.complete_messages))

	# TODO:: figure out why recursion was occurring here. Maybe kill peers that send garbage
	# 			packets? Try to figure out why this caused recursion issues. Check for ascii
	# 			conversion that was done for `test_recursive_stream` and ensure it is correct.
	def test_stream_processor_recursion(self):
		test_stream_processor = StreamProcessor(test_torrent.bitfield)
		test_stream_processor.handshake_occurred = True
		test_stream_processor.parse_stream(test_first_piece_message)

	def test_piece_message(self):
		test_piece_mes = PieceMessage(index=0, begin=0, block=("A"*REQUEST_SIZE))
		test_piece = Piece(524288, 1670, "test_hash",
						   os.path.join(os.path.expanduser("~"), "Downloads/"))
		test_request_mes = RequestMessage(index=0, begin=0)
		test_piece.add_non_completed_request_index(test_request_mes)
		test_piece.append_data(test_piece_mes)

	def test_request_creation(self):
		"""
		Test to check if our method of creating a request produces the same output as a request
		captured off the wire.

		:return: hopefully successful pass
		"""
		test_captured_message = RequestMessage(data=test_captured_request)
		test_created_message = RequestMessage(index=1120, begin=425984)
		self.assertEqual(test_captured_message.index, test_created_message.index)
		self.assertEqual(test_captured_message.begin, test_created_message.begin)
		self.assertEqual(test_captured_message.get_length(), test_created_message.get_length())
		self.assertTrue(test_captured_message.is_equal(test_created_message))

	def test_piece_creation(self):
		test_piece_message = PieceMessage(data=test_captured_piece)

	def test_request_equality(self):
		request1 = RequestMessage(index=0, begin=0)
		request2 = RequestMessage(index=0, begin=0)
		self.assertTrue(request1.is_equal(request2))
