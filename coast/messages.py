from constants import REQUEST_SIZE
from helpermethods import convert_int_to_hex, convert_hex_to_int

"""
Representation of a handshake that is exchanged between the client and peers. Has two init
methods. One for creating a client handshake message to send to peers, and the other to handle
incoming peer handshakes into parsed and usable data by the client.
"""


"""
Stream processor for parsing and assembling messages from a peer TCP stream.
"""

# TODO: all message fields should be raw hex, all get methods should return the int values of
# 		the raw hex data (for len,id fields; raw hex for all other fields)


class StreamProcessor:
	def __init__(self, bitfield):
		self.bitfield = bitfield				# in the form of an array of bits
		self.handshake_occurred = False
		self.current_stream = None
		self.complete_messages = []
		self.final_incomplete_message = None
		self.complete_messages_purged = False
		self.message_header_bytes = [
			"\x00\x00\x00\x01" + "\x00", 										# choke
			"\x00\x00\x00\x01" + "\x01",  										# un-choke
			"\x00\x00\x00\x01" + "\x02", 										# interested
			"\x00\x00\x00\x01" + "\x03",  										# not interested
			"\x00\x00\x00\x05" + "\x04",  										# have
			convert_int_to_hex((len(self.bitfield) / 8 + 1), 4) + "\x05",  		# bitfield
			"\x00\x00\x00\x0d" + "\x06",  										# request
			convert_int_to_hex(REQUEST_SIZE + 1, 4) + "\x07",  					# piece
			"\x00\x00\x00\x0d" + "\x08", 										# cancel
			"\x00\x00\x00\x0d" + "\x09",  										# port
		]

	# TODO: need to disregard data after the incomplete message has been completed and the next
	# 		frame is not a valid frame for a message. This is to deal with the random weird error
	# 		messages being received (`test.test_data.test_broken_piece_message`), or just bad
	# 		data being sent over the wire.
	#
	# 		Use self.message_header_bytes to create specific messages from the stream as opposed
	# 		to generic messages. Or create generic messages after confirming that the first bytes
	# 		are valid message encoding (including bitfield for the torrent and length for piece).

	# TODO: if the message doesn't match..ditch it boiii

	def parse_stream(self, data):
		self.current_stream = data
		"""print ("Current stream (bytes: {}): {}".format(
			len(self.current_stream),
			"0x" + " 0x".join((str(ord(c)) for c in self.current_stream))))"""

		if not len(self.current_stream) > 0:
			print ("(StreamProcessor) No data left to parse.")
		elif not self.handshake_occurred:
			print ("(StreamProcessor) Parsing handshake from stream.")
			peer_handshake = HandshakeMessage(data=self.current_stream)
			# print ("Handshake debug: {}".format(peer_handshake.debug_values()))
			self.handshake_occurred = True
			self.complete_messages.append(peer_handshake)
			self.parse_stream(peer_handshake.leftover_data)
		else:
			if self.final_incomplete_message is not None:
				print ("(StreamProcessor) Adding to incomplete message from stream.")
				self.final_incomplete_message.complete_from_stream(self.current_stream)
				self.parse_stream(self.final_incomplete_message.leftover_data)
				self.complete_messages.append(self.final_incomplete_message)
				self.final_incomplete_message = None
			else:
				print ("(StreamProcessor) Parsing message from stream")
				new_message = Message(self.current_stream)
				# print ("Message debug: {}".format(new_message.debug_values()))
				if new_message.is_complete:
					self.complete_messages.append(new_message)
					self.parse_stream(new_message.leftover_data)
				else:
					self.final_incomplete_message = new_message

	def purge_complete_messages(self):
		self.complete_messages = []


class Message:
	def __init__(self, data=None):
		self.is_complete = False
		self.message_type = "Message"

		if len(data) == 0:
			print ("No data given to Message constructor")

		# special case for keep alive as it has no message_id
		elif len(data) == 4:
			self.raw = data
			self.len_prefix = data[:4]
			self.message_id = "\xff"
			self.payload = ""
			self.leftover_data = data[4:]
		else:
			self.raw = data
			self.len_prefix = data[:4]
			self.message_id = data[4]
			self.payload = data[5:5+convert_hex_to_int(self.len_prefix) - 1]
			self.leftover_data = data[5+convert_hex_to_int(self.len_prefix) - 1:]

			if len(self.payload) == convert_hex_to_int(self.len_prefix) - 1:
				self.is_complete = True

	def complete_from_stream(self, data):
		# TODO: fix this error when parsing piece data from the wire
		# 		(StreamProcessor) Adding to incomplete message from stream.
		# 	Problem parsing a message from the stream
		"""
		File "/Users/spencerdodd/Documents/Programming/coast/coast/messages.py", line 70, in parse_stream
		self.parse_stream(self.final_incomplete_message.leftover_data)
	  	File "/Users/spencerdodd/Documents/Programming/coast/coast/messages.py", line 70, in parse_stream
		self.parse_stream(self.final_incomplete_message.leftover_data)
	  	File "/Users/spencerdodd/Documents/Programming/coast/coast/messages.py", line 69, in parse_stream
		self.final_incomplete_message.complete_from_stream(self.current_stream)
	  	File "/Users/spencerdodd/Documents/Programming/coast/coast/messages.py", line 116, in complete_from_stream
		bytes_left_to_parse = convert_hex_to_int(self.len_prefix) - len(self.payload)
	  	File "/Users/spencerdodd/Documents/Programming/coast/coast/helpermethods.py", line 39, in convert_hex_to_int
		return int(unencoded_input.encode("hex"), 16)
	  	File "/System/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/encodings/hex_codec.py", line 23, in hex_encode
		assert errors == 'strict'
		exceptions.RuntimeError: maximum recursion depth exceeded in cmp

		"""
		bytes_left_to_parse = convert_hex_to_int(self.len_prefix) - len(self.payload)
		self.payload += data[:bytes_left_to_parse]
		self.leftover_data = data[bytes_left_to_parse:]
		self.is_complete = True

	def debug_values(self):
		"""
		Returns string of the message's variable data
		:return: string
		"""
		return "MESSAGE:" + \
			"\n\tRAW" + \
			"\n\t\tlen_prefix (bytes = {}):{} ".format(
				len(self.raw[0:4]), "dec "+" ".join(str(ord(c)) for c in self.raw[0:4])) + \
			"\n\t\tmessage_id (bytes = {}):{}".format(
				len(self.raw[4]), "dec "+str(ord(self.raw[4]))) + \
			"\n\t\tpayload (bytes = {}):{}".format(
				len(self.payload), "dec " + " ".join((str(ord(c)) for c in self.payload))) + \
			"\n\t\tleftover (bytes = {}): {}".format(
				len(self.raw[5+convert_hex_to_int(self.len_prefix):]),
				"dec "+" ".join(str(ord(c)) for c in self.raw[5+convert_hex_to_int(self.len_prefix):])) + \
			"\n\tSTRING" + \
			"\n\t\tlen_prefix:{}\n\t\tmessage_id:{}\n\t\tpayload:{}\n\t\tleftover:{}".format(
				convert_hex_to_int(self.len_prefix),
				convert_hex_to_int(self.message_id),
				self.payload,
				"".join(str(ord(c)) for c in self.leftover_data)
			)

	def get_len_prefix(self):
		return convert_hex_to_int(self.len_prefix)
	def get_message_id(self):
		return convert_hex_to_int(self.message_id)


class HandshakeMessage:
	def __init__(self, info_hash=None, peer_id=None, data=None):
		self.message_type = "Handshake"
		if data is None:
			self.pstrlen = convert_int_to_hex(19, 1)
			self.pstr = "BitTorrent protocol"
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
			self.leftover_data = data[68:]

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
				len(self.pstrlen), "dec "+" ".join(str(ord(c)) for c in self.pstrlen)) + \
			"\n\t\tpstr (bytes = {}): {}".format(
				len(self.pstr), "dec " + " ".join(str(ord(c)) for c in self.pstr)) + \
			"\n\t\treserved (bytes = {}): {}".format(
				len(self.reserved), "dec " + " ".join(str(ord(c)) for c in self.reserved)) + \
			"\n\t\tinfo_hash (bytes = {}): {}".format(
				len(self.info_hash), "dec " + " ".join(str(ord(c)) for c in self.info_hash)) + \
			"\n\t\tpeer_id (bytes = {}): {}".format(
				len(self.peer_id), "dec " + " ".join(str(ord(c)) for c in self.peer_id)) + \
			"\n\t\tleftover (bytes = {}): {}".format(
				len(self.leftover_data), "dec " + " ".join(
					str(ord(c)) for c in self.leftover_data)) + \
			"\n\tSTRING:\n\t\tpstrlen:{}\n\t\tpstr:{}\n\t\tres:{}" + \
			"\n\t\tinfo:{}\n\t\tpeer:{}\n\t\textra:\n\t\t{}".format(
				ord(self.pstrlen),
				self.pstr,
				self.reserved,
				self.info_hash,
				self.peer_id,
				self.leftover_data)

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

	def format_messages(self, messages):
		"""
		Formats message debug strings of an array of messages into a single string for simple
		output.

		:param messages: array of Messages
		:return: string of debug messages for each message in the array
		"""
		output_string = ""
		for message in messages:
			output_string += "\t" + message.debug_values() + "\n"

		return output_string


class KeepAliveMessage(Message):
	def __init__(self, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x00"
			self.message_id = "\xff"
		else:
			Message.__init__(self, data)


class ChokeMessage(Message):
	def __init__(self, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x01"
			self.message_id = "\x00"
		else:
			Message.__init__(self, data)

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}".format(self.len_prefix, self.id)

	def debug_values(self):
		"""
		Debug output for debugging (redundancy is redundant)
		:return:
		"""
		debug_string = "len: {}".format(self.len_prefix) + \
			"id: {}".format(self.id)

		return debug_string


class UnchokeMessage(Message):
	def __init__(self, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x01"
			self.id = "\x01"
		else:
			Message.__init__(self, data)

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}".format(self.len_prefix, self.id)

	def debug_values(self):
		"""
		Debug output for debugging (redundancy is redundant)
		:return:
		"""
		debug_string = "len: {}".format(self.len_prefix) + \
			"id: {}".format(self.id)

		return debug_string


class InterestedMessage(Message):
	def __init__(self, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x01"
			self.message_id = "\x02"
		else:
			Message.__init__(self, data)

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


class NotInterestedMessage(Message):
	def __init__(self, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x01"
			self.message_id = "\x03"
		else:
			Message.__init__(self, data)

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


class HaveMessage(Message):
	def __init__(self, piece_index=None, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x05"
			self.message_id = "\x04"
			self.piece_index = piece_index
			if len(self.piece_index) > int(self.len_prefix.encode("hex", 16)) - 1:
				raise Exception("Payload does not match declared message length")
		else:
			Message.__init__(self, data)
			self.piece_index = self.payload[0:4]

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}{}".format(self.len_prefix, self.message_id, self.payload)

	def debug_values(self):
		"""
		Debug output for debugging (redundancy is redundant)
		:return: debug string
		"""
		debug_string = "len: {}".format(self.len_prefix) + \
			"id: {}".format(self.message_id) + \
			"piece index: {}".format(self.piece_index)

		return debug_string


class BitfieldMessage(Message):
	def __init__(self, bitfield=None, data=None):
		if data is None:
			self.len_prefix = convert_int_to_hex(1+len(bitfield), 4)
			self.message_id = "\x05"
			self.bitfield = bitfield
			if len(self.bitfield) > convert_hex_to_int(self.len_prefix) - 1:
				raise Exception("Payload does not match declared message length")
		else:
			Message.__init__(self, data)
			self.bitfield = self.payload

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}{}".format(self.len_prefix, self.message_id, self.payload)


class RequestMessage(Message):
	def __init__(self, index=None, begin=None, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x0d"
			self.message_id = "\x06"
			self.index = convert_int_to_hex(index, 4)
			self.begin = convert_int_to_hex(begin, 4)
			self.len_prefixgth = convert_int_to_hex(REQUEST_SIZE, 4)
		else:
			Message.__init__(self, data)
			self.index = self.payload[0:4]
			self.begin = self.payload[4:8]
			self.len_prefixgth = self.payload[8:12]

	def debug_values(self):
		debug_string = "len: {}".format(self.len_prefix) + \
				"\nid: {}".format(self.message_id) + \
				"\nindex: {}".format(self.index) + \
				"\nbegin: {}".format(self.begin) + \
				"\nlength: {}".format(self.len_prefixgth)

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
		return "{}{}{}{}{}".format(self.len_prefix, self.message_id, self.index, self.begin, self.len_prefixgth)

	def piece_message_matches_request(self, piece_message):
		"""
		Returns whether or not a given piece message matches the request message
		:param piece_message:
		:return:
		"""
		return self.get_index() == piece_message.get_index() and \
			self.get_begin() == piece_message.get_begin() and \
			self.get_len_prefix() == piece_message.get_len_prefix()

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
		return convert_hex_to_int(self.len_prefix)


class PieceMessage(Message):
	def __init__(self, index=None, begin=None, block=None, data=None):
		if data is None:
			self.len_prefix = convert_int_to_hex(9+len(block), 4)
			self.message_id = "\x07"
			self.index = convert_int_to_hex(index, 4)
			self.begin = convert_int_to_hex(begin, 4)
			self.block = block
		else:
			Message.__init__(self, data)
			self.index = self.payload[0:4]
			self.begin = self.payload[4:8]
			self.block = self.payload[8:]

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


class CancelMessage(Message):
	def __init__(self, index=None, begin=None, length=None, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x0d"
			self.message_id = "\x08"
			self.index = index
			self.begin = begin
			self.len_prefixgth = length
		else:
			Message.__init__(self, data)
			self.index = self.payload[0:4]
			self.begin = self.payload[4:8]
			self.len_prefixgth = self.payload[8:12]

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}{}{}{}".format(self.len_prefix, self.message_id, self.index, self.begin, self.len_prefixgth)


class PortMessage(Message):
	def __init__(self, listen_port=None, data=None):
		if data is None:
			self.len_prefix = "\x00\x00\x00\x0d"
			self.message_id = "\x09"
			self.listen_port = listen_port
		else:
			Message.__init__(self, data)
			self.listen_port = self.payload[0:4]

	def message(self):
		"""
		Gets the value of the choke message to send to the peer
		:return: string of message
		"""
		return "{}{}{}".format(self.len_prefix, self.message_id, self.listen_port)


class EmptyMessage:
	def __init__(self):
		pass
