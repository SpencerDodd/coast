import time
import unittest
from helpermethods import convert_hex_to_int, indent_string
from messages import ChokeMessage, UnchokeMessage, InterestedMessage, InterestedMessage, \
	PieceMessage, HaveMessage, RequestMessage, BitfieldMessage, HandshakeMessage
from bitarray import bitarray
from constants import MAX_OUTSTANDING_REQUESTS, PEER_INACTIVITY_LIMIT

"""
This class represents a peer
"""

# TODO download speed (blocks / time period) -> kb-mb/s

class Peer:
	def __init__(self, torrent, peer_chunk):
		self.ip = ""
		self.port = None
		self.peer_id = None
		self.torrent = torrent # TODO: maybe not best practice
		self.info_hash = None
		self.byte_string_chunk = self.initialize_with_chunk(peer_chunk)
		self.bitfield = bitarray(endian="big")
		self.MESSAGE_ID = {
			0: Peer.process_choke_message,
			1: Peer.process_unchoke_message,
			2: Peer.process_interested_message,
			3: Peer.process_not_interested_message,
			4: Peer.process_have_message,
			5: Peer.process_bitfield_message,
			6: Peer.process_request_message,
			7: Peer.process_piece_message,
			8: Peer.process_cancel_message,
			9: Peer.process_port_message,
			19: Peer.process_handshake_message,
			20: Peer.process_extended_handshake_message,
			255: Peer.process_keep_alive_message
		}
		self.handshake_exchanged = False
		self.received_message_buffer = []
		self.outgoing_messages_buffer = []
		self.request_buffer = [] 				# redundant to self.outgoing_messages_buffer
		self.previous_requests = []
		self.time_of_last_message = time.time()
		# for interaction with Torrent object
		self.current_piece = None
		self.blocks_downloaded = 0

		# our control
		self.am_choking = 1
		self.am_interested = 0

		# peer control
		self.peer_choking = 1
		self.peer_interested = 0

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
		if self.current_piece is None:
			status_string = "-" * 40 + \
							"\nStatus of peer ({})".format(self.peer_id) + \
							"\n\tip: {}".format(self.ip) + \
							"\n\tport: {}".format(self.port) + \
							"\n\tbitfield: {}".format(self.bitfield) + \
							"\n\treceived messages: {}".format(
								"\n\t".join(str(a) for a in self.received_message_buffer)) + \
							"\n\ttime since last message: {}".format(self.time_of_last_message) + \
							"\n\tpiece: {}".format(self.current_piece) + \
							"\n\tam choking: {}".format(self.am_choking) + \
							"\n\tam interested: {}".format(self.am_interested) + \
							"\n\tpeer choking: {}".format(self.peer_choking) + \
							"\n\tpeer interested: {}".format(self.peer_interested) + \
							"\n" + "-" * 40

			return status_string
		else:
			status_string = "-" * 40 + \
							"\nStatus of peer ({})".format(self.peer_id) + \
							"\n\tip: {}".format(self.ip) + \
							"\n\tport: {}".format(self.port) + \
							"\n\tbitfield: {}".format(self.bitfield) + \
							"\n\treceived messages: {}".format(
								"\n\t".join(str(a) for a in self.received_message_buffer)) + \
							"\n\toutgoing messages: {}".format(
								"\n\t".join(
									a.debug_values() for a in self.outgoing_messages_buffer)) + \
							"\n\ttime since last message: {}".format(self.time_of_last_message) + \
							"\n\tpiece: \n{}".format(
								indent_string(self.current_piece.debug_values(), 2)) + \
							"\n\tam choking: {}".format(self.am_choking) + \
							"\n\tam interested: {}".format(self.am_interested) + \
							"\n\tpeer choking: {}".format(self.peer_choking) + \
							"\n\tpeer interested: {}".format(self.peer_interested) + \
							"\n" + "-" * 40

			return status_string

	def received_messages(self, messages):
		"""
		Processes each of the received messages.
		:param messages: Array of received messages from StreamProcessor
		"""
		for message in messages:
			# DEBUG
			# print ("New incoming message: {}".format(str(message)))
			self.time_of_last_message = time.time()
			self.MESSAGE_ID[message.get_message_id()](self, message)

	def get_next_messages(self):
		"""
		Gets the next outgoing messages for the peer protocol based on the newest status of the
		peer. The general flow of messages is:
			- Incoming (remote peer) update peer
			- Torrent updates according to peer changes
			- Peer updates according to torrent changes
			- Protocol sends new messages generated by Peer
		:return: Array of Messages
		"""
		# TODO: we need to think re-requests for non-received or corrupted data
		# 		However, we need to think about re-requests for data that arrived corrupted.
		# 		Maybe we see if a response is a response that is formatted for the given request,
		# 		if so and it takes care of that request, then we send a new request for the next
		# 		block. Otherwise, we discard the data and resend a request. If a peer sends a
		# 		number of failed PieceMessages for a specific request, we blacklist that piece for
		# 		this peer and try another one. If a peer fails too many requests, then we
		# 		drop the peer from active connections (maybe blacklist temporarily inside Torrent),
		# 		and spin up a new peer (in Torrent).

		# DEBUG
		# print ("Getting next messages ...")
		# print ("Removing previous outgoing messages")
		outgoing_message_buffer = []

		if self.am_interested == 0:
			# DEBUG
			# print ("Adding Interested to outgoing messages")
			outgoing_message_buffer.append(InterestedMessage())
			self.am_interested = 1

		# if we have an assigned piece that is not finished, and we haven't sent out the maximum
		# 	number of requests yet: add a new request to our request buffer
		elif self.current_piece is not None and not self.current_piece.is_complete and \
						len(self.request_buffer) < MAX_OUTSTANDING_REQUESTS and \
						self.peer_choking == 0:

			while len(self.request_buffer) < MAX_OUTSTANDING_REQUESTS:
				next_begin = self.current_piece.get_next_begin()
				next_request = RequestMessage(index=self.current_piece.index, begin=next_begin)

				if not self.current_piece.non_completed_request_exists(next_request):
					# DEBUG
					# print ("Adding new request to outgoing messages")
					# print ("Request for index: {}, begin: {}, length: {}".format(
					# 	next_request.get_index(),
					# 	next_request.get_begin(),
					# 	next_request.get_length()
					# ))
					outgoing_message_buffer.append(next_request)
					self.request_buffer.append(next_request)
					self.current_piece.add_non_completed_request_index(next_request)
				else:
					pass
					# DEBUG
					# print ("New request already exists")

		else:
			# DEBUG
			# print ("Not adding any new messages")
			if self.current_piece is not None:
				pass
				# DEBUG
				# print ("BLOCK {}: {}".format(str(self.current_piece.get_index()).rjust(4), self.current_piece.progress_string()))
			else:
				pass
				# DEBUG
				# print ("Peer still doesn't have a piece")
			# DEBUG
			# print ("Requests {} of {}".format(len(self.request_buffer), MAX_OUTSTANDING_REQUESTS))
			# print ("Peer ({}) choking: {}".format(self.peer_id, self.peer_choking == 1))

		# DEBUG
		# print "Received: {}".format(
		# 	",".join(indent_string(str(a), 1) for a in self.received_message_buffer)
		# )
		# DEBUG
		# print "Active Requests: {}".format(",".join(
		# 	"index: {} begin: {}".format(
		# 		a.get_index(),
		# 		a.get_begin()
		# 	) for a in self.request_buffer))
		# DEBUG
		# print "Previous Requests: {}".format(",".join(
		# 	"index: {} begin: {}".format(
		# 		a.get_index(),
		# 		a.get_begin()
		# 	) for a in self.previous_requests))

		self.outgoing_messages_buffer += outgoing_message_buffer
		return outgoing_message_buffer

	def received_bitfield(self):
		return len(self.bitfield.tolist()) > 0

	def update_last_contact(self):
		"""
		Updates the time the last message was sent to the remote peer to determine if a keep-alive
		should be sent. Connections are closed remotely after 2 minutes of inactivity, so if we
		reach around 1:45 we should send a keep-alive message to the peer.
		:return: void
		"""
		pass

	def finished_with_piece(self):
		"""
		Returns true if the piece is done downloading
		:return: boolean
		"""
		return self.current_piece.is_complete()

	def set_next_piece(self, next_piece):
		"""
		Sets the current piece to the given next piece and returns the previous current piece
		to be saved to disk by the torrent.

		:param next_piece: Piece to be downloaded
		:return: Finished piece
		"""
		self.blocks_downloaded += 1
		self.current_piece = next_piece

		# Reset all fields that hold state data
		self.received_message_buffer = []
		self.request_buffer = []
		self.previous_requests = []

	def has_piece(self, index):
		"""
		Returns true if the Peer's bitfield contains the piece at bitarray[index]

		:param index: 0-based index of the piece
		:return: boolean
		"""
		if len(self.bitfield.tolist()) == 0:
			return False
		else:
			return self.bitfield[index] == 1

	def set_piece(self, piece):
		self.current_piece = piece

	def get_messages_in_window(self, window_in_seconds):
		"""

		:param window_in_seconds: number of seconds in the past to parse messages from
		:return: number of piece messages in the window
		"""
		current_time = time.time()
		pieces = 0
		for message in self.received_message_buffer:
			if current_time - message.time_of_creation <= 5 and message.get_message_id() == 7:
				pieces += 1

		return pieces


	"""
	///////////////////////////////////////////////\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
	///////////////////////////////////////////////\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
	||||||||||||||||||||||||||||||||||||| MESSAGE PROCESSING |||||||||||||||||||||||||||||||||||||
	\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\///////////////////////////////////////////////
	\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\///////////////////////////////////////////////
	"""
	def process_handshake_message(self, new_handshake_message):
		self.received_message_buffer.append(new_handshake_message)
		self.peer_id = new_handshake_message.get_peer_id()
		self.info_hash = new_handshake_message.get_info_hash()
		self.handshake_exchanged = True
		# DEBUG
		# print ("Handshake received from peer ({})".format(self.peer_id))

	def process_choke_message(self, new_choke_message):
		self.received_message_buffer.append(new_choke_message)
		# DEBUG
		# print ("Choked by peer ({})".format(self.peer_id))
		self.peer_choking = 1

	def process_unchoke_message(self, new_unchoke_message):
		self.received_message_buffer.append(new_unchoke_message)
		# DEBUG
		# print ("Unchoked by peer ({})".format(self.peer_id))
		self.peer_choking = 0

	def process_interested_message(self, new_interested_message):
		self.received_message_buffer.append(new_interested_message)
		# DEBUG
		# print ("Peer ({}) is interested".format(self.peer_id))
		self.peer_interested = 1

	def process_not_interested_message(self, new_not_interested_message):
		self.received_message_buffer.append(new_not_interested_message)
		# DEBUG
		# print ("Peer ({}) is not interested".format(self.peer_id))
		self.peer_interested = 0

	def process_have_message(self, new_have_message):
		self.received_message_buffer.append(new_have_message)
		piece_index = new_have_message.get_piece_index()
		# DEBUG
		# print ("Peer ({}) has piece {}".format(self.peer_id, piece_index))
		# set the bitarray to all 0s if it doesnt yet exist (to avoid bounds accession error)
		if len(self.bitfield) == 0:
			for i in range(0, len(self.torrent.pieces_hashes)):
				self.bitfield.append(0)
		self.bitfield[piece_index] = 1

	def process_bitfield_message(self, new_bitfield_message):
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
		self.received_message_buffer.append(new_bitfield_message)
		# DEBUG
		# print ("Processing bitfield from peer ({})".format(self.peer_id))
		self.bitfield.frombytes(new_bitfield_message.bitfield)
		self.bitfield.tolist()

	def process_piece_message(self, new_piece_message):
		"""
		Adds a received block to the current piece only if it matches an outstanding request. If
		so, it adds the data to piece and removes the request from the request buffer so that a
		new request can be added to the buffer.

		:param message: received piece message
		:return: void
		"""
		# DEBUG
		# print ("Processing new block message")
		self.received_message_buffer.append(new_piece_message)

		for request_message in self.request_buffer:
			if request_message.piece_message_matches_request(new_piece_message):
				# DEBUG
				# print ("Block is in current piece")
				# add the piece and remove the request.
				self.current_piece.append_data(new_piece_message)
				self.previous_requests.append(request_message)
				self.request_buffer.remove(request_message)

	def process_request_message(self, new_request_message):
		self.received_message_buffer.append(new_request_message)
		# DEBUG
		# print ("Peer ({}) is requesting {}".format(self.peer_id, new_request_message.get_begin()))

	def process_cancel_message(self, new_cancel_message):
		self.received_message_buffer.append(new_cancel_message)
		# DEBUG
		# print ("Peer ({}) has cancelled request for block {}".format(self.peer_id, new_cancel_message.get_begin()))

	def process_port_message(self, new_port_message):
		self.received_message_buffer.append(new_port_message)
		# DEBUG
		# print ("Peer ({}) has sent port {}".format(self.peer_id, new_port_message.get_port()))

	def process_extended_handshake_message(self, message):
		self.received_message_buffer.append(message)
		# DEBUG
		# print ("Peer ({}) has sent extension {}".format(self.peer_id, message.debug_values()))

	def process_keep_alive_message(self, new_keepalive_message):
		self.received_message_buffer.append(new_keepalive_message)
		# DEBUG
		# print ("Peer ({}) has sent a keep-alive message")
