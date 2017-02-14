from __future__ import print_function
import os
import sys
import time
import urllib
import bencode
import hashlib
import requests
import traceback
from twisted.internet import reactor, task

from constants import MAX_PEERS, ERROR_BYTESTRING_CHUNKSIZE
from peer import Peer
from piece import Piece
from messages import HandshakeMessage
from protocols import PeerFactory
from helpermethods import one_directory_back, make_dir, tally_messages_by_type

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
		self.started = False
		self.is_complete = False
		self.last_request = None
		self.last_announce = None
		self.reannounce_limit = None
		self.metadata_initialized = False
		self.event_set = False
		self.last_response_object = None
		self.connected_peers = 0
		self.active_peers = []
		self.active_peer_indices = []
		self.assigned_pieces = []

		# Data fields
		self.download_root = os.path.join(os.path.expanduser("~"), "Downloads/")
		self.temporary_download_location = None
		self.peers = []
		self.bitfield = []
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

		# Make the temp dir for piece downloading
		make_dir(os.path.join(self.download_root))

		# establish existing progress from earlier session
		self.initialize_previously_downloaded_progress()

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
					self.download_root = os.path.join(self.download_root, self.torrent_name)

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

		Also sets self.bitfield as a bitfield array for tracking download progress
		"""
		self.pieces_hashes = [self.metadata["pieces"][x:x+20] for x in range(0, len(self.metadata["pieces"]), 20)]

		for x in range(0, (len(self.metadata["info"]["pieces"]) / 20)):
			self.bitfield.append(0)

		# DEBUG
		# print ("Initialization"+("-"*20))
		# print ("Pieces: {}, Bitfield_len: {}".format(len(self.pieces_hashes), len(self.bitfield)))

	def initialize_previously_downloaded_progress(self):
		"""
		from os import listdir
		from os.path import isfile, join
		onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
		"""
		self.temporary_download_location = os.path.join(self.download_root, "tmp/")
		make_dir(os.path.join(self.temporary_download_location))

		piece_files = [f for f in os.listdir(self.temporary_download_location) if
					   os.path.isfile(os.path.join(self.temporary_download_location, f))]
		for file_name in piece_files:
			self.bitfield[int(file_name.split(".")[0])] = 1

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
				new_peer = Peer(self, peer_chunk)
				self.peers.append(new_peer)

	def chunk_bytestring(self, input, length=6):
		"""
		Chunks a bytestring into an array of (default) 6-byte pieces

		Used for:
			parsing bytestring for peers into individual peers
	"""
		if len(input) > 0 and len(input) % length != 0:
			raise Exception(ERROR_BYTESTRING_CHUNKSIZE)
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

		handshake_message = HandshakeMessage(info_hash=info_hash, peer_id=peer_id).message()
		return handshake_message

	def send_tracker_request(self):
		""" Sends the request to the tracker for the given torrent"""
		torrent_request = self.get_tracker_request()
		response = requests.get(torrent_request)
		self.process_tracker_response(response)

	def connect_to_peers(self):
		""" Connects to the peers in the 'peers' field of the object"""
		print ("Connect To Peers")
		loops = 0
		while len(self.active_peers) < MAX_PEERS:
			if loops < len(self.peers):
				loops += 1
				# TODO: more advanced algo for picking peer to add
				# 	maybe try all unique peers in peers before retrying peers that were disconnected
				# 	after we've tried all peers, maybe we re-request the tracker and try to get
				# 	an updated peer list, etc...
				# DEBUG
				print ("trying to find a new peer (connected: {} / {}) [loops: {}]".format(len(self.active_peers), MAX_PEERS, loops))
				current_peer_index = self.connected_peers % len(self.peers)
				current_peer = self.peers[current_peer_index]
				if current_peer not in self.active_peers:
					reactor.connectTCP(current_peer.ip, current_peer.port, PeerFactory(self, reactor, current_peer))
					self.active_peers.append(current_peer)
					self.connected_peers += 1
			else:
				break

	def start_torrent(self):
		""" Starts the torrent by connecting to the peers and running the twisted reactor"""
		self.send_tracker_request()
		self.connect_to_peers()
		# DEBUG
		# l = task.LoopingCall(self.peer_activity_update)
		# l.start(1.0)
		reactor.run()

	def get_progress(self):
		pieces_finished = self.bitfield.count(1)
		return float(pieces_finished) / len(self.bitfield) * 100

	def print_status(self):
		sys.stdout.flush()
		status_string = "Torrent Progress\n" + \
			u"{}% {}\n".format("{0:.2f}".format(self.get_progress()).rjust(6), int(self.get_progress()) * u'\u2588')
		status_string += "ACTIVE PEERS\n"
		for peer in self.active_peers:
			if peer.current_piece is not None:
				# DEBUG
				status_string += "Peer: {} ".format(str(peer.ip).rjust(15)) + \
						" Recv: {}".format(str(len(peer.received_message_buffer)).rjust(4)) + \
						" Sent: {}".format(str(len(peer.outgoing_messages_buffer)).rjust(4)) + \
						" Total: {}mb ".format(str(float(peer.blocks_downloaded) / 2).rjust(7)) + \
						" Block {}: {}\n".format(str(peer.current_piece.get_index()).rjust(4), peer.current_piece.progress_string())
			else:
				status_string += "Peer: {} ".format(str(peer.ip).rjust(15)) + \
					   " Recv: {}".format(str(0).rjust(4)) + \
					   " Sent: {}".format(str(0).rjust(4)) + \
					   " Total: {}mb ".format(str(float(0)).rjust(7)) + \
					   " Block {}: {}\n".format("None".rjust(4), "0.0%".rjust(6))

		print (status_string)
		# print (status_string, end="\r")

	def remove_active_peer(self, peer):
		"""
		Removes a peer from the torrent's peer list
		:param peer: Peer to be removed
		:return: void
		"""
		# DEBUG
		print ("Removing peer from active list ({})".format(peer.peer_id))
		self.active_peers.remove(peer)
		if peer.current_piece is not None:
			try:
				self.assigned_pieces.remove(peer.current_piece.get_index())
			except Exception as e:
				pass
				# DEBUG
				error_message = "Problem removing piece" + \
					"\nPiece: {}".format(peer.current_piece.get_index()) + \
					"\nAssigned: {}".format(", ".join(str(c) for c in self.assigned_pieces))

				# TODO: if we don't try-block wrap...why is the index being removed before this piece is done???
				# 	or is this an index accession error because another peer is erroneously removing
				# 	our piece? Or is this because we assigned the same piece to more than one peer?
				print (error_message)

		# DEBUG
		print ("Remove active peer: Adding a new peer")
		self.connect_to_peers()

	def process_next_round(self, peer):
		"""
		The main processing step after a peer has performed some actions. Need to check and see
		if the peer has any data to process, or if we need to send a response to the peer in the
		form of a message to be sent.

		:return:
		"""
		if peer.current_piece is not None and peer.current_piece.is_complete:
			# DEBUG
			# print ("Peer has completed downloading piece... Assigning a new piece")
			# self.save_completed_peer_piece_to_disk(peer.set_next_piece(self.get_next_piece_for_download(peer)))
			piece_to_save = peer.current_piece
			if piece_to_save.data_matches_hash():
				self.exchange_completed_piece_for_new_piece(peer)
			else:
				# DEBUG
				print ("Piece was corrupted... Trying again")
				peer.set_next_piece(piece_to_save.reset())

			self.update_completion_status()

		elif peer.current_piece is None and peer.received_bitfield():
			# DEBUG
			print ("Peer has bitfield but no piece... Assigning a piece")
			peer.set_piece(self.get_next_piece_for_download(peer))

		elif not peer.received_bitfield():
			pass
			# DEBUG
			print ("Peer has no bitfield... Waiting for bitfield to give piece assignment")
		else:
			pass
			# DEBUG
			print ("Proceeding as usual... No update from torrent")

	# TODO
	def update_completion_status(self):
		pass

	def save_completed_peer_piece_to_disk(self, piece_to_save):
		"""
		Iterates through peers and takes completed pieces from them with the peer method for saving
		a piece and updates the pieces array by flipping the bit at the given index of the piece
		to 1.

		:param piece_to_save:
		:return:
		"""
		# DEBUG
		# print ("Saving piece to disk")
		# set the given piece of the bitarray to 1
		piece_to_save.write_to_temporary_storage()
		self.bitfield[piece_to_save.get_index()] = 1
		# DEBUG
		# print ("Finished saving piece to disk")

	def exchange_completed_piece_for_new_piece(self, peer):
		# DEBUG
		print ("Exchanging piece for new piece")
		print ("Current piece: {}".format(peer.current_piece.get_index()))
		# self.assigned_pieces.remove(peer.current_piece.get_index())
		self.bitfield[peer.current_piece.get_index()] = 1
		self.save_completed_peer_piece_to_disk(peer.current_piece)
		next_piece = self.get_next_piece_for_download(peer)
		# DEBUG
		print ("New piece: {}".format(next_piece.get_index()))
		peer.set_next_piece(next_piece)

	def get_next_piece_for_download(self, peer):
		# DEBUG
		print ("Getting peer a new piece")
		for index, bit in enumerate(self.bitfield):
			# DEBUG
			print ("current_index: {}\nassigned: {}\nbitfield at index: {}".format(index,", ".join(str(c) for c in self.assigned_pieces), self.bitfield[index]))
			if index not in self.assigned_pieces and self.bitfield[index] == 0:
				# DEBUG
				print ("Giving peer piece {} for download".format(index))
				next_hash = self.pieces_hashes[index]
				next_piece = Piece(self.metadata["piece_length"], index, next_hash, self.download_root)
				self.assigned_pieces.append(index)
				# DEBUG
				print ("Assigned: {}".format(",".join(str(x) for x in self.assigned_pieces)))
				return next_piece
		# DEBUG
		print ("Finished giving peer a new piece")

	def main_control_loop(self):
		"""
		Main control flow is as follows:
			1. check if torrent is done
				a. if so compile each file piece into it's parent file
			2. check if we can re-announce and get more peers

		:return:
		"""
		if not self.started:
			self.start_torrent()
			self.started = True

		if self.is_complete:
			pass
			# compile pieces into file
			# update torrent status? (or do that in core)

		if (time.time() - self.last_announce) > self.reannounce_limit:
			pass
