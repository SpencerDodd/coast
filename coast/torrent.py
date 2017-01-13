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
from piece import Piece
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
		self.torrent_name = None
		self._announce = None

		# Metadata fields
		self.metadata = {
			"info": None,
			"announce": None,
			"announce-list": None,
			"creation_date": None,
			"comment": None,
			"created_by": None,
			"encoding": None,
			"piece_length": None,
			"pieces": None
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
		self.active_peers = []

		# Data fields
		self.download_location = os.path.join(os.path.expanduser("~"), "Downloads/")
		self.peers = []
		self.pieces = []
		self.pieces_hashes = []

		try:
			self.initialize_metadata_from_file()
		except Exception as e:
			raise Exception("Problem processing .torrent file\n{}".format(e.message))

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
					self.metadata["piece_length"] = decoded_data["info"]["piece length"]
					self.metadata["pieces"] = decoded_data["info"]["pieces"]
					self.torrent_name = self.metadata["info"]["name"]
					# set the download location to dir + name
					os.path.join(self.download_location, self.torrent_name)

					# initialize our pieces dict from the pieces string
					self.initialize_pieces()

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

	def initialize_pieces(self):
		"""
		Initializes the pieces array from the .torrent file metadata. Slices the pieces string
		into 20-byte segments that represent the SHA1-hash of the piece's data

		Also sets self.pieces as a bitfield array for tracking download progress
		"""
		self.pieces_hashes = [self.metadata["pieces"][x:x+20] for x in range(0, len(self.metadata["pieces"]) / 20)]

		for x in range(0, (len(self.metadata["info"]["pieces"]) / 20 / 8)):
			self.pieces.append(0)

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

		handshake_message = Handshake(info_hash=info_hash, peer_id=peer_id).message()
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
			self.active_peers.append(current_peer)
			self.connected_peers += 1

	def start_torrent(self):
		""" Starts the torrent by connecting to the peers and running the twisted reactor"""
		self.send_tracker_request()
		self.connect_to_peers()
		reactor.run()

	def remove_active_peer(self, peer):
		"""
		Removes a peer from the torrent's peer list
		:param peer: Peer to be removed
		:return: void
		"""
		print ("Removing peer from active list <<||{}||>>".format(peer.peer_id))
		self.active_peers.remove(peer)

	def process_next_round(self, peer):
		"""
		The main processing step after a peer has performed some actions. Need to check and see
		if the peer has any data to process, or if we need to send a response to the peer in the
		form of a message to be sent.

		:return:
		"""
		if peer.current_piece is not None and peer.current_piece.is_complete:
			self.save_completed_peer_piece_to_disk(peer.get_next_piece(self.get_next_piece_for_download(peer)))
		elif peer.received_bitfield():
			# give the peer a piece
			peer.set_piece(self.get_next_piece_for_download(peer))
		else:
			# wait until the peer gets a bitfield
			print ("Torrent waiting until peer gets a bitfield to give a piece assignment")

	def save_completed_peer_piece_to_disk(self, piece_to_save):
		"""
		Iterates through peers and takes completed pieces from them with the peer method for saving
		a piece and updates the pieces array by flipping the bit at the given index of the piece
		to 1.

		:param piece_to_save:
		:return:
		"""
		pass

	def get_next_piece_for_download(self, peer):
		next_index = self.pieces.index(0)
		if peer.has_piece(next_index):
			print ("Giving peer piece {} for download".format(next_index))
			next_hash = self.pieces_hashes[next_index]
			next_piece = Piece(self.metadata["piece_length"], next_index, next_hash, self.download_location)
			return next_piece
		else:
			print ("Couldn't find a piece")


if __name__ == "__main__":
	test_peer_id = "-CO0001-5208360bf90d"
	test_port = 6881
	root_dir = one_directory_back(os.getcwd())
	test_data_directory = os.path.join(root_dir, "test/")
	test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
	test_torrent_file_path = os.path.join(test_data_directory, test_torrent_file)
	test_torrent = Torrent(test_peer_id, test_port, test_torrent_file_path)

	test_torrent.start_torrent()