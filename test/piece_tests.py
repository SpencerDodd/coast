import os
import unittest

from coast.piece import Piece
from coast.torrent import Torrent
from coast.messages import PieceMessage
from coast.helpermethods import one_directory_back

from test.test_data import test_broken_piece_message, test_piece_message


class PieceTests(unittest.TestCase):

	def test_piece_creation(self):
		test_peer_id = "-CO0001-5208360bf90d"
		test_port = 6881
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test/")
		test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent_file_path = os.path.join(test_data_directory, test_torrent_file)
		test_torrent = Torrent(test_peer_id, test_port, test_torrent_file_path)

		test_piece_size = test_torrent.metadata["piece_length"]
		test_piece_index = 0
		test_piece_hash = test_torrent.pieces_hashes[test_piece_index]
		test_download_location = test_torrent.download_location

		test_piece_block = PieceMessage(data=test_piece_message)
		test_piece = Piece(test_piece_size, test_piece_index, test_piece_hash, test_download_location)
		self.assertEqual(0.0, test_piece.progress)
		test_piece.append_data(test_piece_block)
		self.assertEqual(3.125, test_piece.progress)
		# check to ensure that overwriting doesn't change progress
		test_piece.append_data(test_piece_block)
		self.assertEqual(3.125, test_piece.progress)
		# check to see if our bytes were downloaded
		self.assertEqual(16384, len([val for val in test_piece.data if val != 0]))
		# check to see if our next index is correct
		self.assertEqual(16384, test_piece.get_next_begin())
