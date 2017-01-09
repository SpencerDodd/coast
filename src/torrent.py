import os
import time
import urllib
import bencode
import hashlib
import requests
import unittest
import traceback
from twisted.internet import reactor

import constants
from peer import Peer
from messages import Handshake
from protocols import PeerFactory
from constants import PROTOCOL_STRING
from helpermethods import one_directory_back, convert_int_to_hex

# Error messages



"""
This class represents a torrent. It holds information (metadata) about the torrent
as parsed from the .torrent file.
"""


class Torrent:
	def __init__(self, peer_id, port, torrent_file_path):
		""" initializes the torrent

		:param peer_id -> the peer id of the client
		:param port -> the port over which connections about the torrent are
			made
		"""
		self.peer_id = peer_id
		self.port = port
		self.torrent_file_path = torrent_file_path

		# Metadata fields
		self.metadata = {
			"info": None,
			"announce": None,
			"announce-list": None,
			"creation_date": None,
			"comment": None,
			"created_by": None,
			"encoding": None
		}

		# Tracker request fields
		self.tracker_request = {
			"info_hash": None,
			"peer_id": None,
			"port": None,
			"uploaded": 0,
			"downloaded": 0,
			"left": None,
			"compact": 0,
			"no_peer_id": 0,
			"event": "started",
			"ip": None,
			"numwant": 200,
			"key": None,
			"trackerid": None
		}

		# Tracker response fields
		self.tracker_response = {
			"failure reason": None,
			"warning message": None,
			"interval": None,
			"min interval": None,
			"tracker id": None,
			"complete": None,
			"incomplete": None,
			"peers": None,
		}

		# Status fields for the torrent
		self.last_request = None
		self.last_announce = None
		self.metadata_initialized = False
		self.event_set = False
		self.last_response_object = None
		self.connected_peers = 0

		# Data fields
		self.download_location = os.path.join(os.path.expanduser("~"), "Downloads/")
		self.peers = []

		try:
			self.initialize_metadata_from_file()
		except:
			raise Exception("Torrent file not valid")

		# Initialize the tracker request fields
		self.tracker_request["peer_id"] = peer_id
		self.tracker_request["port"] = port
		self.tracker_request["info_hash"] = self.generate_info_hash()
		self.tracker_request["left"] = self.metadata["info"]["length"]

	def initialize_metadata_from_file(self):
		"""Fills in torrent information by reading from a metadata file (.torrent)

		:param metadata_file_path -> string path of the location of the .torrent
		file"""

		# check if we have a torrent file
		if ".torrent" == self.torrent_file_path[-8:]:
			try:
				with open(self.torrent_file_path, "r") as metadata_file:
					metadata = metadata_file.read()
					decoded_data = bencode.bdecode(metadata)

					# fill in our essential fields
					self._announce = decoded_data["announce"]
					self.metadata["info"] = decoded_data["info"]

					# fill in our optional fields if they exist
					meta_keys = decoded_data.keys()
					if "announce-list" in meta_keys:
						self.metadata["announce_list"] = decoded_data["announce-list"]
					if "creation date" in meta_keys:
						self.metadata["creation_date"] = decoded_data["creation date"]
					if "comment" in meta_keys:
						self.metadata["comment"] = decoded_data["comment"]
					if "created by" in meta_keys:
						self.metadata["created_by"] = decoded_data["created by"]
					if "encoding" in meta_keys:
						self.metadata["encoding"] = decoded_data["encoding"]

				self.metadata_initialized = True

			except Exception as e:
				error_message = "File is improperly formatted\n{}".format(traceback.format_exc(e))
				raise ValueError(error_message)


		else:
			raise ValueError("File is not .torrent type")

	def can_request(self):
		"""
		Returns true if the torrent can make an announce request

		Relevant standards information / response fields:
		---------------------------------------------------------------------------
		interval: Interval in seconds that the client should wait between sending
			regular requests to the tracker
		min interval: (optional) Minimum announce interval. If present clients must
			not reannounce more frequently than this.
		---------------------------------------------------------------------------
		"""

		if self.last_request is not None:
			time_since_request = time.time() - self.last_request

			if self.tracker_response["interval"] is None:
				return True

			elif time_since_request > self.tracker_response["interval"]:
				return True

			else:
				return False
		else:
			return True

	def generate_ascii_info_hash(self):
		"""
		Generates an ascii hash of the bencoded info dict
		"""
		bencoded_info_dict = bencode.bencode(self.metadata["info"])
		return hashlib.sha1(bencoded_info_dict).hexdigest()

	def generate_hex_info_hash(self):
		"""
		Generates a hex hash of the bencoded info dict
		"""
		bencoded_info_dict = bencode.bencode(self.metadata["info"])
		return hashlib.sha1(bencoded_info_dict).digest()

	def generate_info_hash(self):
		"""
		Generates the final URL-encoded hash of the hex hash of the bencoded info
		dict.

		Reserves RFC unreserved characters -_.!~*'()
		"""
		sha1_hash = self.generate_hex_info_hash()
		url_encoded_hash = urllib.quote(sha1_hash, safe="-_.!~*'()")
		return url_encoded_hash

	def get_tracker_request(self):
		"""
		Return a string representing a request to make to the torrent's tracker.
		This request is handled by the NetworkHandler.

		The tracker is an HTTP/HTTPS service which responds to HTTP GET requests.
		The requests include metrics from clients that help the tracker keep
		overall statistics about the torrent. The response includes a peer list
		that helps the client participate in the torrent. The base URL consists
		of the "announce URL" as defined in the metainfo (.torrent) file. The
		parameters are then added to this URL, using standard CGI methods (i.e.
		a '?' after the announce URL, followed by 'param=value' sequences separated
		by '&').
		"""

		request_text = "{}?info_hash={}".format(self._announce, self.tracker_request["info_hash"])

		for request_field in self.tracker_request.keys():
			field_data = self.tracker_request[request_field]
			if request_field is not "info_hash" and field_data is not None:
				request_text += "&{}={}".format(request_field, field_data)

		return request_text

	def process_tracker_response(self, tracker_response):
		"""
		input: String, output: void

		Updates the torrent based on a response from the tracker
		"""
		self.last_response_object = tracker_response
		response_text = tracker_response.text
		decoded_response = bencode.bdecode(response_text)

		for response_field in decoded_response.keys():
			self.tracker_response[response_field] = decoded_response[response_field]

		self.populate_peers()

	def get_last_response(self):
		"""
		Returns the last response received by the torrent from the tracker
		"""
		return self.last_response_object

	def populate_peers(self):
		"""
		Creates peer objects from the peer field (hex) of the response object
		from the tracker
		"""
		if self.tracker_response["peers"] is None:
			raise Exception("Peers not populated (check tracker response)")

		else:
			# noinspection PyTypeChecker
			chunked_peers = self.chunk_bytestring(self.tracker_response["peers"])
			for peer_chunk in chunked_peers:
				new_peer = Peer(peer_chunk)
				self.peers.append(new_peer)

	def chunk_bytestring(self, input, length=6):
		"""
		Chunks a bytestring into an array of (default) 6-byte pieces

		Used for:
			parsing bytestring for peers into individual peers
	"""
		if len(input) > 0 and len(input) % length != 0:
			raise Exception(constants.ERROR_BYTESTRING_CHUNKSIZE)
		else:
			return [input[x:x + length] for x in range(0, len(input), length)]

	def get_handshake(self):
		""" Return the handshake message to send to a newly connected peer

		handshake: <pstrlen><pstr><reserved><info_hash><peer_id>
			:pstrlen -> length of pstr as a single raw byte
			:pstr -> string identifier of the protocol
			:reserved -> 8 reserved bits (all 0s)
			:info_hash -> SHA1 of the info key
			:peer_id -> client peer_id
		"""
		info_hash = self.generate_hex_info_hash()
		peer_id = self.peer_id

		handshake_message = Handshake(info_hash=info_hash, peer_id=peer_id).get_string()
		return handshake_message

	def send_tracker_request(self):
		""" Sends the request to the tracker for the given torrent"""
		torrent_request = self.get_tracker_request()
		response = requests.get(torrent_request)
		self.process_tracker_response(response)

	def connect_to_peers(self):
		""" Connects to the peers in the 'peers' field of the object"""
		while self.connected_peers < constants.MAX_PEERS:
			current_peer = self.peers[self.connected_peers]
			reactor.connectTCP(current_peer.ip, current_peer.port, PeerFactory(self, current_peer))
			self.connected_peers += 1

	def	get_next_message_for_peer(self, peer):
		pass





	def start_torrent(self):
		""" Starts the torrent by connecting to the peers and running the twisted reactor"""
		self.send_tracker_request()
		self.connect_to_peers()
		reactor.run()


"""
###############################################################################
###############################################################################
###############################################################################
#################################### Tests ####################################
###############################################################################
###############################################################################
###############################################################################
"""


class TestTorrent(unittest.TestCase):
	def test_urlencode_hash(self):
		test_peer_id = "-CO0001-5208360bf90d"
		test_port = 6881
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test_data/")
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
		test_data_directory = os.path.join(root_dir, "test_data/")
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
		test_data_directory = os.path.join(root_dir, "test_data/")
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
		test_data_directory = os.path.join(root_dir, "test_data/")
		test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent_file_path = os.path.join(test_data_directory, test_torrent_file)
		test_torrent = Torrent(test_peer_id, test_port, test_torrent_file_path)

		test_peer_chunk = u"N\xe6\xcd2\xc5DN\xe6\xcd2\xc5D"
		expected_chunks = 2

		self.assertEqual(expected_chunks, len(test_torrent.chunk_bytestring(test_peer_chunk)))

		test_broken_chunk = u"N\xe6\xcd2\xc5DN\xe6\xcd2\xc5De"
		with self.assertRaises(Exception) as context:
			test_torrent.chunk_bytestring(test_broken_chunk)
		self.assertTrue(constants.ERROR_BYTESTRING_CHUNKSIZE in context.exception)

	def test_populate_peers(self):
		test_peer_id = "-CO0001-5208360bf90d"
		test_port = 6881
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test_data/")
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
		test_peer_id = "-CO0001-5208360bf90d"
		test_port = 6881
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test_data/")
		test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent_file_path = os.path.join(test_data_directory, test_torrent_file)
		test_torrent = Torrent(test_peer_id, test_port, test_torrent_file_path)

		self.assertEqual(convert_int_to_hex(19), '\x13')

	def test_handshake_message(self):
		test_peer_id = "-CO0001-5208360bf90d"
		test_port = 6881
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test_data/")
		test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent_file_path = os.path.join(test_data_directory, test_torrent_file)
		test_torrent = Torrent(test_peer_id, test_port, test_torrent_file_path)

		expected_info_hash = '\x13BitTorrent protocol\x00\x00\x00\x00\x00\x00\x00\x00' + \
				'\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z-CO0001-5208360bf90d'

		self.assertEqual(expected_info_hash, test_torrent.get_handshake())


	def test_run(self):
		test_peer_id = "-CO0001-5208360bf90d"
		test_port = 6881
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test_data/")
		test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent_file_path = os.path.join(test_data_directory, test_torrent_file)
		test_torrent = Torrent(test_peer_id, test_port, test_torrent_file_path)

		test_torrent.start_torrent()



if __name__ == "__main__":
	unittest.main()
