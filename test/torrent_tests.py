import os
import urllib
import unittest

from coast.peer import Peer
from coast.torrent import Torrent
from coast.constants import ERROR_BYTESTRING_CHUNKSIZE
from coast.helpermethods import one_directory_back, convert_int_to_hex
from test.test_data import test_torrent


class TestTorrent(unittest.TestCase):
	def test_urlencode_hash(self):
		test_peer_id = "-CO0001-5208360bf90d"
		test_port = 6881
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test/")
		test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent_file_path = os.path.join(test_data_directory, test_torrent_file)
		test_torrent = Torrent(test_peer_id, test_port, test_torrent_file_path)

		test_sha1_hash = "0403fb4728bd788fbcb67e87d6feb241ef38c75a"
		text_hex_hash = "\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z"
		expected_url_hash = "%04%03%FBG(%BDx%8F%BC%B6~%87%D6%FE%B2A%EF8%C7Z"

		self.assertEqual(expected_url_hash, urllib.quote(text_hex_hash, safe="-_.!~*'()"))
		self.assertEqual(text_hex_hash, test_torrent.generate_hex_info_hash())

	def test_metadate_from_file(self):
		test_peer_id = "-CO0001-5208360bf90d"
		test_port = 6881
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test/")
		test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent_file_path = os.path.join(test_data_directory, test_torrent_file)
		test_torrent = Torrent(test_peer_id, test_port, test_torrent_file_path)

		expected_announce = "http://torrent.ubuntu.com:6969/announce"
		expected_announce_list = [
			["http://torrent.ubuntu.com:6969/announce"],
			["http://ipv6.torrent.ubuntu.com:6969/announce"]
		]
		expected_info = {}

		expected_info["length"] = 1593835520
		expected_info["name"] = "ubuntu-16.10-desktop-amd64.iso"
		expected_info["piece length"] = 524288
		expected_info_hash = "%04%03%FBG(%BDx%8F%BC%B6~%87%D6%FE%B2A%EF8%C7Z"
		# expected_info["pieces"] = (Omitted due to size and gibberish)

		self.assertEqual(expected_announce, test_torrent._announce)
		self.assertEqual(expected_announce_list, test_torrent.metadata["announce_list"])
		self.assertEqual(expected_info["length"], test_torrent.metadata["info"]["length"])
		self.assertEqual(expected_info["name"], test_torrent.metadata["info"]["name"])
		self.assertEqual(expected_info["piece length"], test_torrent.metadata["info"]["piece length"])
		self.assertEqual(60800, len(test_torrent.metadata["info"]["pieces"]))
		self.assertEqual(expected_info_hash, test_torrent.generate_info_hash())

	def test_tracker_request(self):
		test_peer_id = "-CO0001-5208360bf90d"
		test_port = 6881
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test/")
		test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent_file_path = os.path.join(test_data_directory, test_torrent_file)
		test_torrent = Torrent(test_peer_id, test_port, test_torrent_file_path)

		expected_request = "http://torrent.ubuntu.com:6969/announce?info_h" + \
						   "ash=%04%03%FBG(%BDx%8F%BC%B6~%87%D6%FE%B2A%EF8%C7Z&uploaded=0&dow" + \
						   "nloaded=0&event=started&compact=0&numwant=200&no_peer_id=0&port=6" + \
						   "881&peer_id=-Co0001-7a673c102d18&left=1593835520"

		test_request = test_torrent.get_tracker_request()

		# remove the peer ids from both requests as they vary with each use
		exp_peer_index = expected_request.index("&peer_id")
		parsed_expected = expected_request[:exp_peer_index] + \
						  expected_request[exp_peer_index + 29:]
		test_peer_index = test_request.index("&peer_id")
		parsed_test = test_request[:test_peer_index] + \
					  test_request[test_peer_index + 29:]

		# make sure we parsed correctly
		correct_parsed_test = "http://torrent.ubuntu.com:6969/announce?inf" + \
							  "o_hash=%04%03%FBG(%BDx%8F%BC%B6~%87%D6%FE%B2A%EF8%C7Z&uploaded=0&" + \
							  "downloaded=0&event=started&compact=0&numwant=200&no_peer_id=0&por" + \
							  "t=6881&left=1593835520"
		self.assertEqual(parsed_test, correct_parsed_test)
		# compare our generated vs. expected
		self.assertEqual(parsed_expected, parsed_test)

	def test_chunk_bytestring(self):
		test_peer_id = "-CO0001-5208360bf90d"
		test_port = 6881
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test/")
		test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent_file_path = os.path.join(test_data_directory, test_torrent_file)
		test_torrent = Torrent(test_peer_id, test_port, test_torrent_file_path)

		test_peer_chunk = u"N\xe6\xcd2\xc5DN\xe6\xcd2\xc5D"
		expected_chunks = 2

		self.assertEqual(expected_chunks, len(test_torrent.chunk_bytestring(test_peer_chunk)))

		test_broken_chunk = u"N\xe6\xcd2\xc5DN\xe6\xcd2\xc5De"
		with self.assertRaises(Exception) as context:
			test_torrent.chunk_bytestring(test_broken_chunk)
		self.assertTrue(ERROR_BYTESTRING_CHUNKSIZE in context.exception)

	def test_populate_peers(self):
		test_peer_id = "-CO0001-5208360bf90d"
		test_port = 6881
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test/")
		test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent_file_path = os.path.join(test_data_directory, test_torrent_file)
		test_torrent = Torrent(test_peer_id, test_port, test_torrent_file_path)

		test_tracker_response = {
			'incomplete': 110,
			'min interval': None,
			'complete': 2957,
			'failure reason': None,
			'tracker id': None,
			'interval': 1800,
			'peers': u">\xd2\xf0\x9a\xceh\xa6F\xd3 \x1a\x90\x1f\xdc,\xb4" + \
					 u"\xc8\xd5\xd5B\x1c\xc8\xc8\xdcWa\x01\xfb\xc8\xd5%\xbbp" + \
					 u"\x9a\xc8\xd5^\x17\xdc\x8d\xd9\x03\xd1\x86_%\xc8\xd5\xb0" + \
					 u"\xd7\x1e\xb2\xc8\xd5\xc0\x83,\x11\xd9$\xb26\xa5\xe9\x1a" + \
					 u"\xe1\xb9A\x86Mb\xda\x8aD\x06\x0f\x1b\x15Og\xfa\x83M*Rd" + \
					 u"\xf8\n\xc8\xd5\\\x8d\x95\x80\xc8\xd5\x18q\x95S\xc8\xd5N" + \
					 u"\xc1X;\xe5\x05m\xbe/\xf2\xc8\xd5L\x1b>\x91\xc8\xd5\xb9" + \
					 u"\x15\xd9!\xf0\x90C\xbc\x00\xbd#'%\x8f\xfc\x88H\xb7\x88<" + \
					 u"\xab\xf1#'m|\t609%\x04\xec\x13\xc8\xd6M\xa4W>\xc0[\x88=|" + \
					 u"\xb9om.\xe4\xe7>\xc8\xd5\xa3\xac\xdb0\x1bW\xb9/\x85C<f" + \
					 u"\xb9-\xc3\xc3N'[M\x8c(\xc8\xd5\x96er\r\xdd\x0c%\xbbt8>" + \
					 u"\x9a\xad\xff\xf7r\xfa}\x95[YL\xc8\xd5\x05\t\x99\xd6\x1a" + \
					 u"\x89V\xab|6\xc3Pc\xc6\xabv\xef\xfa\xbc\x98`\x8dQ\xd4b" + \
					 u"\xdc\x0c\x8c\xc8\xd5\x9c\xc4\xd7\xcd\x1a\xe1%\xcc#\x86" + \
					 u"\xe3\x08U\x11\x1e\xcb\xee\x8dD\x8e%\x1f#'Ln\x85w\xf4)@[" + \
					 u"\x06\xf4\xc8\xd5L\x11)\xc9\xe0^D\xe6Bb\xc91",
			u'warning message': None}
		test_torrent.tracker_response["peers"] = test_tracker_response["peers"]
		test_torrent.populate_peers()
		# check that the number of peers created == bytes / 6
		self.assertEqual(len(test_tracker_response["peers"]) / 6, len(test_torrent.peers))

	def test_hex_conversions(self):
		self.assertEqual(convert_int_to_hex(19, 1), '\x13')

	def test_handshake_message(self):

		expected_info_hash = '\x13BitTorrent protocol\x00\x00\x00\x00\x00\x00\x00\x00' + \
				'\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z-CO0001-5208360bf90d'

		self.assertEqual(expected_info_hash, test_torrent.get_handshake())

	def test_remove_active_peer(self):
		test_tracker_response = {
			'incomplete': 110,
			'min interval': None,
			'complete': 2957,
			'failure reason': None,
			'tracker id': None,
			'interval': 1800,
			'peers': u">\xd2\xf0\x9a\xceh\xa6F\xd3 \x1a\x90\x1f\xdc,\xb4" + \
					 u"\xc8\xd5\xd5B\x1c\xc8\xc8\xdcWa\x01\xfb\xc8\xd5%\xbbp" + \
					 u"\x9a\xc8\xd5^\x17\xdc\x8d\xd9\x03\xd1\x86_%\xc8\xd5\xb0" + \
					 u"\xd7\x1e\xb2\xc8\xd5\xc0\x83,\x11\xd9$\xb26\xa5\xe9\x1a" + \
					 u"\xe1\xb9A\x86Mb\xda\x8aD\x06\x0f\x1b\x15Og\xfa\x83M*Rd" + \
					 u"\xf8\n\xc8\xd5\\\x8d\x95\x80\xc8\xd5\x18q\x95S\xc8\xd5N" + \
					 u"\xc1X;\xe5\x05m\xbe/\xf2\xc8\xd5L\x1b>\x91\xc8\xd5\xb9" + \
					 u"\x15\xd9!\xf0\x90C\xbc\x00\xbd#'%\x8f\xfc\x88H\xb7\x88<" + \
					 u"\xab\xf1#'m|\t609%\x04\xec\x13\xc8\xd6M\xa4W>\xc0[\x88=|" + \
					 u"\xb9om.\xe4\xe7>\xc8\xd5\xa3\xac\xdb0\x1bW\xb9/\x85C<f" + \
					 u"\xb9-\xc3\xc3N'[M\x8c(\xc8\xd5\x96er\r\xdd\x0c%\xbbt8>" + \
					 u"\x9a\xad\xff\xf7r\xfa}\x95[YL\xc8\xd5\x05\t\x99\xd6\x1a" + \
					 u"\x89V\xab|6\xc3Pc\xc6\xabv\xef\xfa\xbc\x98`\x8dQ\xd4b" + \
					 u"\xdc\x0c\x8c\xc8\xd5\x9c\xc4\xd7\xcd\x1a\xe1%\xcc#\x86" + \
					 u"\xe3\x08U\x11\x1e\xcb\xee\x8dD\x8e%\x1f#'Ln\x85w\xf4)@[" + \
					 u"\x06\xf4\xc8\xd5L\x11)\xc9\xe0^D\xe6Bb\xc91",
			u'warning message': None}
		test_torrent.tracker_response["peers"] = test_tracker_response["peers"]
		test_torrent.populate_peers()
		current_peer_index = 0

		#test_peer = Peer(test_torrent.peers[0])

		current_peer = test_torrent.peers[current_peer_index]
		test_torrent.active_peers.append(current_peer)
		test_torrent.connected_peers += 1

		#test_torrent.remove_active_peer()
