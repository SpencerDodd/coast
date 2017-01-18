from constants import REQUEST_SIZE, PROTOCOL_STRING
from helpermethods import convert_int_to_hex, convert_hex_to_int, format_hex_output
import traceback
"""
Representation of a handshake that is exchanged between the client and peers. Has two init
methods. One for creating a client handshake message to send to peers, and the other to handle
incoming peer handshakes into parsed and usable data by the client.
"""


"""
Stream processor for parsing and assembling messages from a peer TCP stream.
"""


class StreamProcessor:
	def __init__(self, torrent):
		self.torrent = torrent
		self.stream = ""
		self.completed_stream_messages = []
		self.incomplete_stream = None
		self.message_headers = {
			"\x13\x42\x69\x74\x54": {
				"create_method": self.create_handshake_message,
				"byte_size": 68
			},
			"\x00\x00\x00\x00": {
				"create_method": self.create_keepalive_message,
				"byte_size": 4
			},
			"\x00\x00\x00\x00\x00": {
				"create_method": self.create_keepalive_message,
				"byte_size": 4
			},
			"\x00\x00\x00\x01" + "\x00": {
				"create_method": self.create_choke_message,
				"byte_size": 5
			},
			"\x00\x00\x00\x01" + "\x01": {
				"create_method": self.create_unchoke_message,
				"byte_size": 5
			},
			"\x00\x00\x00\x01" + "\x02": {
				"create_method": self.create_interested_message,
				"byte_size": 5
			},
			"\x00\x00\x00\x01" + "\x03": {
				"create_method": self.create_notinterested_message,
				"byte_size": 5
			},
			"\x00\x00\x00\x05" + "\x04": {
				"create_method": self.create_have_message,
				"byte_size": 9
			},
			convert_int_to_hex(1 + (len(self.torrent.pieces_hashes) / 8), 4) + "\x05": {
				"create_method": self.create_bitfield_message,
				"byte_size": len(self.torrent.pieces_hashes) / 8 + 5
			},
			"\x00\x00\x00\x0d" + "\x06": {
				"create_method": self.create_request_message,
				"byte_size": 17
			},
			convert_int_to_hex(9 + REQUEST_SIZE, 4) + "\x07": {
				"create_method": self.create_piece_message,
				"byte_size": 13 + REQUEST_SIZE
			},
			"\x00\x00\x00\x0d" + "\x08": {
				"create_method": self.create_cancel_message,
				"byte_size": 17
			},
			"\x00\x00\x00\x03" + "\x09": {
				"create_method": self.create_port_message,
				"byte_size": 7
			}
		}

	def parse_stream(self, stream_data=None):
		if stream_data is not None:
			self.stream += stream_data

		# if our stream could contain a complete message (keep-alive)... parse it
		if len(self.stream) >= 4:
			# DEBUG
			# print ("Current Stream: {}".format(format_hex_output(self.stream)))

			# check to make sure the stream has enough data in it to parse out the first message
			required_bytes = self.message_headers[self.stream[0:5]]["byte_size"]

			# DEBUG
			# print ("Next message requires {} bytes".format(required_bytes))

			if len(self.stream) < required_bytes:
				pass
				# DEBUG
				# print ("---Waiting for more data to complete stream")
				# print (format_hex_output(self.stream))
			else:
				try:
					# DEBUG
					# print ("---Appending new complete message")
					new_complete_message = self.message_headers[self.stream[:5]]["create_method"](data=self.stream[:required_bytes])
					self.completed_stream_messages.append(new_complete_message)
					self.stream = self.stream[required_bytes:]
					self.parse_stream()
				except Exception as e:
					# DEBUG
					# print ("---Stream data was not properly formatted... Dropping stream")
					# print (traceback.format_exc(e))
					self.stream = ""

	def get_complete_messages(self):
		"""
		Returns the streams that represent the data of a complete message
		:return:
		"""
		return self.completed_stream_messages

	def purge_complete_messages(self):
		self.completed_stream_messages = []

	def create_handshake_message(self, data=None):
		# DEBUG
		# print ("Creating a new handshake message")
		return HandshakeMessage(data=data)

	def create_keepalive_message(self, data=None):
		# DEBUG
		#  print ("Creating a new keepalive message")
		return KeepAliveMessage(data=data)

	def create_choke_message(self, data=None):
		# DEBUG
		#  print ("Creating a new choke message")
		return ChokeMessage(data=data)

	def create_unchoke_message(self, data=None):
		# DEBUG
		#  print ("Creating a new unchoke message")
		return UnchokeMessage(data=data)

	def create_interested_message(self, data=None):
		# DEBUG
		#  print ("Creating a new interested message")
		return InterestedMessage(data=data)

	def create_notinterested_message(self, data=None):
		# DEBUG
		#  print ("Creating a new notinterested message")
		return NotInterestedMessage(data=data)

	def create_have_message(self, data=None):
		# DEBUG
		#  print ("Creating a new have message")
		return HaveMessage(data=data)

	def create_bitfield_message(self, data=None):
		# DEBUG
		#  print ("Creating a new bitfield message")
		return BitfieldMessage(data=data)

	def create_request_message(self, data=None):
		# DEBUG
		#  print ("Creating a new request message")
		return RequestMessage(data=data)

	def create_piece_message(self, data=None):
		# DEBUG
		#  print ("Creating a new piece message")
		return PieceMessage(data=data)

	def create_cancel_message(self, data=None):
		# DEBUG
		#  print ("Creating a new cancel message")
		return CancelMessage(data=data)

	def create_port_message(self, data=None):
		# DEBUG
		#  print ("Creating a new port message")
		return PortMessage(data=data)


class HandshakeMessage:
	def __init__(self, info_hash=None, peer_id=None, data=None):
		if data is None:
			self.pstrlen = convert_int_to_hex(19, 1)
			self.pstr = PROTOCOL_STRING
			self.reserved = "\x00\x00\x00\x00\x00\x00\x00\x00"
			self.info_hash = info_hash
			self.peer_id = peer_id
		else:
			self.raw = data
			self.pstrlen = data[0]
			self.pstr = data[1:20]
			self.reserved = data[20:28]
			self.info_hash = data[28:48]
			self.peer_id = data[48:68]

			if self.pstrlen != "\x13":
				raise Exception("Not a valid handshake message (pstrlen [ex]: {} [actual]: {})".format("\x13", self.pstrlen))
			elif str(self.pstr) != PROTOCOL_STRING:
				raise Exception(
					"Not a valid handshake message (pstr [ex]: {} [actual]: {})".format(PROTOCOL_STRING,
																						  self.pstr))
			elif len(self.reserved) != 8:
				raise Exception(
					"Not a valid handshake message (reserved [ex]: {} [actual]: {})".format(
						8,
						len(self.reserved)))
			elif len(self.info_hash) != 20:
				raise Exception(
					"Not a valid handshake message (info_hash[ex]: {} [actual]: {})".format(
						20,
						len(self.info_hash)))
			elif len(self.peer_id) != 20:
				raise Exception(
					"Not a valid handshake message (peer_id[ex]: {} [actual]: {})".format(
						20,
						len(self.pstr)))

	def message(self):
		"""
		Provides a formatted handshake message as a string to pass over the TCP connection

		:return:  string form handshake message
		"""
		handshake_message = "{}{}{}{}{}".format(
			self.pstrlen,
			self.pstr,
			self.reserved,
			self.info_hash,
			self.peer_id)

		return handshake_message

	def debug_values(self):
		"""
		Returns string of the handshake's variable data
		:return: string
		"""
		return "HANDSHAKE" + \
			"\n\tRAW" + \
			"\n\t\tpstrlen (bytes = {}): {}".format(
				len(self.pstrlen), format_hex_output(self.pstrlen)) + \
			"\n\t\tpstr (bytes = {}): {}".format(
				len(self.pstr), format_hex_output(self.pstr)) + \
			"\n\t\treserved (bytes = {}): {}".format(
				len(self.reserved), format_hex_output(self.reserved)) + \
			"\n\t\tinfo_hash (bytes = {}): {}".format(
				len(self.info_hash),format_hex_output(self.info_hash)) + \
			"\n\t\tpeer_id (bytes = {}): {}".format(
				len(self.peer_id), format_hex_output(self.peer_id))

	def get_pstrlen(self):
		return convert_hex_to_int(self.pstrlen)

	def get_pstr(self):
		return self.pstr

	def get_message_id(self):
		return convert_hex_to_int(self.pstrlen)

	def get_info_hash(self):
		return self.info_hash

	def get_peer_id(self):
		return self.peer_id


class KeepAliveMessage:
	def __init__(self, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x00"
			self.message_id = "\xff"
		else:
			self.len_prefix = data[0:4]
			self.message_id = "\xff"

			if self.len_prefix != "\x00\x00\x00\x00":
				raise Exception("Not valid NotInterested (len prefix: {})".format(format_hex_output(self.len_prefix)))
			elif self.message_id != "\xff":
				raise Exception("Not valid NotInterested (message id: {})".format(format_hex_output(self.message_id)))
			elif len(data) != 4:
				raise Exception("Not a valid NotInterested message: ({})".format(format_hex_output(data)))

	def get_len_prefix(self):
		return convert_hex_to_int(self.len_prefix)

	def get_message_id(self):
		return convert_hex_to_int(self.message_id)


class ChokeMessage:
	def __init__(self, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x01"
			self.message_id = "\x00"
		else:
			self.len_prefix = data[0:4]
			self.message_id = data[4]

			if self.len_prefix != "\x00\x00\x00\x01":
				raise Exception("Not valid Choke (len prefix: {})".format(format_hex_output(self.len_prefix)))
			elif self.message_id != "\x00":
				raise Exception("Not valid Choke (message id: {})".format(format_hex_output(self.message_id)))
			elif len(data) != 5:
				raise Exception("Not a valid Choke message: ({})".format(format_hex_output(data)))

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}".format(self.len_prefix, self.message_id)

	def debug_values(self):
		"""
		Debug output for debugging (redundancy is redundant)
		:return:
		"""
		debug_string = "len: {}".format(self.len_prefix) + \
			"id: {}".format(self.message_id)

		return debug_string

	def get_len_prefix(self):
		return convert_hex_to_int(self.len_prefix)

	def get_message_id(self):
		return convert_hex_to_int(self.message_id)


class UnchokeMessage:
	def __init__(self, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x01"
			self.message_id = "\x01"
		else:
			self.len_prefix = data[0:4]
			self.message_id = data[4]

			if self.len_prefix != "\x00\x00\x00\x01":
				raise Exception("Not valid Unchoke (len prefix: {})".format(format_hex_output(self.len_prefix)))
			elif self.message_id != "\x01":
				raise Exception("Not valid Unchoke (message id: {})".format(format_hex_output(self.message_id)))
			elif len(data) != 5:
				raise Exception("Not a valid Unchoke message: ({})".format(format_hex_output(data)))

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}".format(self.len_prefix, self.message_id)

	def debug_values(self):
		"""
		Debug output for debugging (redundancy is redundant)
		:return:
		"""
		debug_string = "len: {}".format(self.len_prefix) + \
			"id: {}".format(self.message_id)

		return debug_string

	def get_len_prefix(self):
		return convert_hex_to_int(self.len_prefix)

	def get_message_id(self):
		return convert_hex_to_int(self.message_id)


class InterestedMessage:
	def __init__(self, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x01"
			self.message_id = "\x02"
		else:
			self.len_prefix = data[0:4]
			self.message_id = data[4]

			if self.len_prefix != "\x00\x00\x00\x01":
				raise Exception("Not valid Interested (len prefix: {})".format(format_hex_output(self.len_prefix)))
			elif self.message_id != "\x02":
				raise Exception("Not valid Interested (message id: {})".format(format_hex_output(self.message_id)))
			elif len(data) != 5:
				raise Exception("Not a valid Interested message: ({})".format(format_hex_output(data)))

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}".format(self.len_prefix, self.message_id)

	def debug_values(self):
		"""
		Debug output for debugging (redundancy is redundant)
		:return:
		"""
		debug_string = "len: {}".format(self.len_prefix) + \
			"id: {}".format(self.message_id)

		return debug_string

	def get_len_prefix(self):
		return convert_hex_to_int(self.len_prefix)

	def get_message_id(self):
		return convert_hex_to_int(self.message_id)


class NotInterestedMessage:
	def __init__(self, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x01"
			self.message_id = "\x03"
		else:
			self.len_prefix = data[0:4]
			self.message_id = data[4]

			if self.len_prefix != "\x00\x00\x00\x01":
				raise Exception("Not valid NotInterested (len prefix: {})".format(format_hex_output(self.len_prefix)))
			elif self.message_id != "\x03":
				raise Exception("Not valid NotInterested (message id: {})".format(format_hex_output(self.message_id)))
			elif len(data) != 5:
				raise Exception("Not a valid NotInterested message: ({})".format(format_hex_output(data)))

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}".format(self.len_prefix, self.message_id)

	def debug_values(self):
		"""
		Debug output for debugging (redundancy is redundant)
		:return:
		"""
		debug_string = "len: {}".format(self.len_prefix) + \
			"id: {}".format(self.message_id)

		return debug_string

	def get_len_prefix(self):
		return convert_hex_to_int(self.len_prefix)

	def get_message_id(self):
		return convert_hex_to_int(self.message_id)


class HaveMessage:
	def __init__(self, piece_index=None, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x05"
			self.message_id = "\x04"
			self.piece_index = piece_index
		else:
			self.len_prefix = data[0:4]
			self.message_id = data[4]
			self.piece_index = data[5:9]

			if self.len_prefix != "\x00\x00\x00\x05":
				raise Exception("Not valid Have (len prefix: {})".format(format_hex_output(self.len_prefix)))
			elif self.message_id != "\x04":
				raise Exception("Not valid Have (message id: {})".format(format_hex_output(self.message_id)))
			elif len(data) != 9:
				raise Exception("Not a valid Have message: ({})".format(format_hex_output(data)))

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}{}".format(self.len_prefix, self.message_id, self.piece_index)

	def debug_values(self):
		"""
		Debug output for debugging (redundancy is redundant)
		:return: debug string
		"""
		debug_string = "len: {}".format(self.len_prefix) + \
			"id: {}".format(self.message_id) + \
			"piece index: {}".format(self.piece_index)

		return debug_string

	def get_len_prefix(self):
		return convert_hex_to_int(self.len_prefix)

	def get_message_id(self):
		return convert_hex_to_int(self.message_id)

	def get_piece_index(self):
		return convert_hex_to_int(self.piece_index)


class BitfieldMessage:
	def __init__(self, bitfield=None, data=None):
		if data is None:
			self.len_prefix = convert_int_to_hex(1+len(bitfield), 4)
			self.message_id = "\x05"
			self.bitfield = bitfield
			if len(self.bitfield) > convert_hex_to_int(self.len_prefix) - 1:
				raise Exception("Payload does not match declared message length")
		else:
			self.len_prefix = data[0:4]
			self.message_id = data[4]
			self.bitfield = data[5:4+convert_hex_to_int(self.len_prefix)]

			if convert_hex_to_int(self.len_prefix) != len(data) - 4:
				raise Exception("Not valid Bitfield (len prefix: {})".format(format_hex_output(self.len_prefix)))
			elif self.message_id != "\x05":
				raise Exception("Not valid Bitfield (message id: {})".format(format_hex_output(self.message_id)))
			elif len(self.bitfield) != convert_hex_to_int(self.len_prefix) - 1:
				raise Exception("Not valid Bitfield (len bitfield: [exp] {}, [act] {})".format(format_hex_output(self.len_prefix - 1, len(self.bitfield))))
			if convert_hex_to_int(self.len_prefix) != len(data) - 4:
				raise Exception("Not valid Bitfield [bytes {}] {}".format(len(self.bitfield), format_hex_output(data)))

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}{}".format(self.len_prefix, self.message_id, self.bitfield)

	def get_len_prefix(self):
		return convert_hex_to_int(self.len_prefix)

	def get_message_id(self):
		return convert_hex_to_int(self.message_id)


class RequestMessage:
	def __init__(self, index=None, begin=None, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x0d"
			self.message_id = "\x06"
			self.index = convert_int_to_hex(index, 4)
			self.begin = convert_int_to_hex(begin, 4)
			self.length = convert_int_to_hex(REQUEST_SIZE, 4)
		else:
			self.len_prefix = data[0:4]
			self.message_id = data[4]
			self.index = data[5:9]
			self.begin = data[9:13]
			self.length = data[13:17]

			# TODO: valid index checking here?
			if self.len_prefix != "\x00\x00\x00\x0d":
				raise Exception("Not valid Request (len prefix: {})".format(format_hex_output(self.len_prefix)))
			elif self.message_id != "\x06":
				raise Exception("Not valid Request (message id: {})".format(format_hex_output(self.message_id)))
			elif self.length != convert_int_to_hex(REQUEST_SIZE, 4):
				raise Exception(
					"Not a valid Request message: (length: {})".format(format_hex_output(self.length)))
			elif len(data) != 17:
				raise Exception(
					"Not valid Request (data: {})".format(format_hex_output(data)))

	def debug_values(self):
		debug_string = "len: {}".format(self.len_prefix) + \
				"\nid: {}".format(self.message_id) + \
				"\nindex: {}".format(self.index) + \
				"\nbegin: {}".format(self.begin) + \
				"\nlength: {}".format(self.length)

		return debug_string

	def is_equal(self, other):
		"""
		Checks for equality between requests
		:param other:
		:return:
		"""
		return self.get_len_prefix() == other.get_len_prefix() and \
				self.get_message_id() == other.get_message_id() and \
				self.get_index() == other.get_index() and \
			   	self.get_begin() == other.get_begin() and \
			   	self.get_length() == other.get_length()

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}{}{}{}".format(self.len_prefix, self.message_id, self.index, self.begin, self.length)

	def piece_message_matches_request(self, piece_message):
		"""
		Returns whether or not a given piece message matches the request message
		:param piece_message:
		:return:
		"""
		# DEBUG
		# print "Comparing given block to request"
		# print "Requested index: {}, Block index: {}".format(self.get_index(), piece_message.get_index())
		# print "Requested begin: {}, Block begin: {}".format(self.get_begin(), piece_message.get_begin())
		# print "Requested block size: {}, Block block size: {}".format(self.get_length(), piece_message.get_length())

		return self.get_index() == piece_message.get_index() and \
			self.get_begin() == piece_message.get_begin() and \
			self.get_length() == piece_message.get_length()

	"""
	Getters for if you want the integer values
	"""
	def get_len_prefix(self):
		return convert_hex_to_int(self.len_prefix)

	def get_message_id(self):
		return convert_hex_to_int(self.message_id)

	def get_index(self):
		return convert_hex_to_int(self.index)

	def get_begin(self):
		return convert_hex_to_int(self.begin)

	def get_length(self):
		return convert_hex_to_int(self.length)


class PieceMessage:
	def __init__(self, index=None, begin=None, block=None, data=None):
		if data is None:
			self.len_prefix = convert_int_to_hex(9+REQUEST_SIZE, 4)
			self.message_id = "\x07"
			self.index = convert_int_to_hex(index, 4)
			self.begin = convert_int_to_hex(begin, 4)
			self.block = block

			if self.get_length() != int(REQUEST_SIZE):
				raise Exception(
					"Block size is fucked (expected: {}, actual: {})".format(REQUEST_SIZE,
																			 self.get_length()) +
					"\nBlock: " + "".join(str(ord(c)) for c in self.block)
				)
		else:
			self.len_prefix = data[0:4]
			self.message_id = data[4]
			self.index = data[5:9]
			self.begin = data[9:13]
			self.block = data[13:13+REQUEST_SIZE]

			if convert_hex_to_int(self.len_prefix) != len(data) - 4:
				raise Exception("Not valid Piece (len prefix: {})".format(format_hex_output(self.len_prefix)))
			elif self.message_id != "\x07":
				raise Exception("Not valid Piece (message id: {})".format(format_hex_output(self.message_id)))
			elif len(self.block) != REQUEST_SIZE:
				raise Exception(
					"Not a valid Piece: (block size: {})".format(format_hex_output(len(self.block))))

	def debug_values(self):
		debug_string = "PIECE MESSAGE" + \
				"\nlen: {}".format(self.len_prefix) + \
				"\nid: {}".format(self.message_id) + \
				"\nindex: {}".format(self.index) + \
				"\nbegin: {}".format(self.begin) + \
				"\nblock (bytes = {})".format(len(self.block)
				)

		return debug_string

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}{}{}{}".format(self.len_prefix, self.message_id, self.index, self.begin, self.block)

	"""
		Getters for if you want the integer values
		"""

	def get_len_prefix(self):
		return convert_hex_to_int(self.len_prefix)

	def get_message_id(self):
		return convert_hex_to_int(self.message_id)

	def get_index(self):
		return convert_hex_to_int(self.index)

	def get_begin(self):
		return convert_hex_to_int(self.begin)

	def get_length(self):
		return len(self.block)


class CancelMessage:
	def __init__(self, index=None, begin=None, length=None, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x0d"
			self.message_id = "\x08"
			self.index = index
			self.begin = begin
			self.length = length
		else:
			self.len_prefix = data[0:4]
			self.message_id = data[4]
			self.index = data[5:9]
			self.begin = data[9:13]
			self.length = data[13:17]

			if self.len_prefix != "\x00\x00\x00\x0d":
				raise Exception("Not valid Cancel (len prefix: {})".format(format_hex_output(self.len_prefix)))
			elif self.message_id != "\x08":
				raise Exception("Not valid Cancel (message id: {})".format(format_hex_output(self.message_id)))
			elif len(data) != 17:
				raise Exception(
					"Not valid Cancel (data: {})".format(format_hex_output(data)))

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}{}{}{}".format(self.len_prefix, self.message_id, self.index, self.begin, self.len_prefix)

	def get_len_prefix(self):
		return convert_hex_to_int(self.len_prefix)

	def get_message_id(self):
		return convert_hex_to_int(self.message_id)


class PortMessage:
	def __init__(self, listen_port=None, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x03"
			self.message_id = "\x09"
			self.listen_port = listen_port
		else:
			self.len_prefix = data[0:4]
			self.message_id = data[4]
			self.listen_port = data[5:7]

			if self.len_prefix != "\x00\x00\x00\x03":
				raise Exception("Not valid Port (len prefix: {})".format(format_hex_output(self.len_prefix)))
			elif self.message_id != "\x09":
				raise Exception("Not valid Port (message id: {})".format(format_hex_output(self.message_id)))
			elif len(data) != 7:
				raise Exception(
					"Not valid Port (data: {})".format(format_hex_output(data)))

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}{}".format(self.len_prefix, self.message_id, self.listen_port)

	def get_len_prefix(self):
		return convert_hex_to_int(self.len_prefix)

	def get_message_id(self):
		return convert_hex_to_int(self.message_id)

	def get_port(self):
		return convert_hex_to_int(self.listen_port)


class EmptyMessage:
	def __init__(self):
		pass
