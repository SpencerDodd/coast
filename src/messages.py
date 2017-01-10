import unittest

from helpermethods import convert_int_to_hex

"""
Representation of a handshake that is exchanged between the client and peers. Has two init
methods. One for creating a client handshake message to send to peers, and the other to handle
incoming peer handshakes into parsed and usable data by the client.
"""


"""
Stream processor for parsing and assembling messages from a peer TCP stream.
"""


class StreamProcessor:
	def __init__(self):
		self.handshake_occurred = False
		self.current_stream = None
		self.complete_messages = []
		self.final_incomplete_message = None
		self.complete_messages_purged = False

	def parse_stream(self, data):
		self.current_stream = data
		print ("Current stream (bytes: {}): {}".format(len(self.current_stream), "0x" + " 0x".join((str(ord(c)) for c in self.current_stream))))

		if not len(self.current_stream) > 0:
			print ("(StreamProcessor) No data left to parse.")
		elif not self.handshake_occurred:
			print ("(StreamProcessor) Parsing handshake from stream.")
			peer_handshake = Handshake(data=self.current_stream)
			print ("Handshake debug: {}".format(peer_handshake.debug_values()))
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
				print ("Message debug: {}".format(new_message.debug_values()))
				if new_message.is_complete:
					self.complete_messages.append(new_message)
					self.parse_stream(new_message.leftover_data)
				else:
					self.final_incomplete_message = new_message

	def purge_complete_messages(self):
		self.complete_messages = []


class Handshake:
	def __init__(self, info_hash=None, peer_id=None, data=None):
		self.message_type = "Handshake"
		if data is None:
			self.pstrlen = convert_int_to_hex(19)
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

	def get_string(self):
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
			"\n\t\tpstrlen (bytes = {}): {}".format(len(self.pstrlen), "0x"+" 0x".join(str(ord(c)) for c in self.pstrlen)) + \
			"\n\t\tpstr (bytes = {}): {}".format(len(self.pstr), "0x" + " 0x".join(str(ord(c)) for c in self.pstr)) + \
			"\n\t\treserved (bytes = {}): {}".format(len(self.reserved), "0x" + " 0x".join(str(ord(c)) for c in self.reserved)) + \
			"\n\t\tinfo_hash (bytes = {}): {}".format(len(self.info_hash), "0x" + " 0x".join(str(ord(c)) for c in self.info_hash)) + \
			"\n\t\tpeer_id (bytes = {}): {}".format(len(self.peer_id), "0x" + "0x".join(str(ord(c)) for c in self.peer_id)) + \
			"\n\t\tleftover (bytes = {}): {}".format(len(self.leftover_data), "0x" + " 0x".join(str(ord(c)) for c in self.leftover_data)) + \
			"\n\tSTRING:\n\t\tpstrlen:{}\n\t\tpstr:{}\n\t\tres:{}\n\t\tinfo:{}\n\t\tpeer:{}\n\t\textra:\n\t\t{}".format(
				ord(self.pstrlen),
				self.pstr,
				self.reserved,
				self.info_hash,
				self.peer_id,
				self.leftover_data)

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


class Message:
	def __init__(self, data=None):
		self.is_complete = False
		self.message_type = "Message"

		if len(data) == 0:
			print ("No data given to Message constructor")
		else:
			self.raw = data
			self.len_prefix = int(data[:4].encode("hex"), 16)
			self.message_id = str(ord(data[4]))
			self.payload = data[5:5+self.len_prefix - 1]
			self.leftover_data = data[5+self.len_prefix - 1:]

			if len(self.payload) == self.len_prefix - 1:
				self.is_complete = True

	def complete_from_stream(self, data):
		bytes_left_to_parse = self.len_prefix - len(self.payload)
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
			"\n\t\tlen_prefix (bytes = {}):{} ".format(len(self.raw[0:4]), "0x"+" 0x".join(str(ord(c)) for c in self.raw[0:4])) + \
			"\n\t\tmessage_id (bytes = {}):{}".format(len(self.raw[4]), "0x"+str(ord(self.raw[4]))) + \
			"\n\t\tpayload (bytes = {}):{}".format(len(self.payload), "0x" + " 0x".join((str(ord(c)) for c in self.payload))) + \
			"\n\t\tleftover (bytes = {}): {}".format(len(self.raw[5+self.len_prefix:]), "0x"+" 0x".join(str(ord(c)) for c in self.raw[5+self.len_prefix:])) + \
			"\n\tSTRING" + \
			"\n\t\tlen_prefix:{}\n\t\tmessage_id:{}\n\t\tpayload:{}\n\t\tleftover:{}".format(
			self.len_prefix,
			self.message_id,
			self.payload,
			"".join(str(ord(c)) for c in self.leftover_data)
		)


class MessageTests(unittest.TestCase):
	def test_client_handshake(self):
		test_info_hash = "\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z"
		test_peer_id = "-CO0001-5208360bf90d"
		test_handshake = Handshake(info_hash=test_info_hash, peer_id=test_peer_id)
		expected_handshake_string = "\x13BitTorrent protocol\x00\x00\x00\x00\x00\x00\x00" + \
				"\x00\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z-CO0001-5208360bf90d"
		self.assertEqual(expected_handshake_string, test_handshake.get_string())

	def test_peer_handshake(self):
		test_handshake_data = "\x13" + \
				"\x42\x69\x74\x54\x6f\x72\x72\x65\x6e\x74\x20\x70\x72\x6f\x74\x6f\x63\x6f\x6c" + \
				"\x00\x00\x00\x00\x00\x00\x00\x00" + \
				"\x04\x03\xfb\x47\x28\xbd\x78\x8f\xbc\xb6\x7e\x87\xd6\xfe\xb2\x41\xef\x38\xc7\x5a" + \
				"\x2d\x43\x4f\x30\x30\x30\x31\x2d\x35\x32\x30\x38\x33\x36\x30\x62\x66\x39\x30\x64"

		test_handshake = Handshake(data=test_handshake_data)
		expected_handshake_string = "\x13BitTorrent protocol\x00\x00\x00\x00\x00\x00\x00" + \
				"\x00\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z-CO0001-5208360bf90d"
		self.assertEqual(expected_handshake_string, test_handshake.get_string())

	def test_captured_peer_handshake(self):
		captured_handshake = "\x13\x42\x69\x74\x54\x6f\x72\x72\x65\x6e\x74\x20\x70\x72\x6f\x74" + \
							 "\x6f\x63\x6f\x6c\x00\x00\x00\x00\x00\x10\x00\x05\x04\x03\xfb\x47" + \
							 "\x28\xbd\x78\x8f\xbc\xb6\x7e\x87\xd6\xfe\xb2\x41\xef\x38\xc7\x5a" + \
							 "\x2d\x71\x42\x33\x33\x41\x30\x2d\x6f\x2d\x67\x30\x34\x79\x7a\x4f" + \
							 "\x28\x21\x2e\x6c"
		captured_handshake = Handshake(data=captured_handshake)
		expected_handshake_string = "\x13" + \
				"BitTorrent protocol" + \
				"\x00\x00\x00\x00\x00\x10\x00\x05" + \
				"\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z" + \
				"-qB33A0-o-g04yzO(!.l"

		self.assertEqual(expected_handshake_string, captured_handshake.get_string())

	def test_stream_processor(self):
		test_stream = "\x13\x42\x69\x74\x54\x6f\x72\x72\x65\x6e\x74\x20\x70\x72\x6f\x74\x6f\x63" \
					  "\x6f\x6c\x00\x00\x00\x00\x00\x10\x00\x01\x04\x03\xfb\x47\x28\xbd\x78\x8f" \
					  "\xbc\xb6\x7e\x87\xd6\xfe\xb2\x41\xef\x38\xc7\x5a\x2d\x4d\x4c\x33\x2e\x31" \
					  "\x2e\x35\x2d\x87\x20\xa8\x31\xd8\x3a\x4d\xa3\x4a\x02\x92\x00\x00\x00\x1a" \
					  "\x14\x00\x64\x31\x3a\x6d\x64\x31\x31\x3a\x75\x74\x5f\x6d\x65\x74\x61\x64" \
					  "\x61\x74\x61\x69\x31\x65\x65\x65\x00\x00\x01\x7d\x05\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff" \
					  "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00" \
					  "\x01\x00"

		test_stream_processor = StreamProcessor()
		test_stream_processor.parse_stream(test_stream)
		self.assertEqual(4, len(test_stream_processor.complete_messages))

	# TODO:: figure out why recursion was occurring here. Maybe kill peers that send garbage
	# TODO::	packets? Try to figure out why this caused recursion issues. Check for ascii
	# TODO::	conversion that was done for `test_recursive_stream` and ensure it is correct.
	def test_stream_processor_recursion(self):
		test_recursive_stream = "\x00\x00\x05\x04\x00\x00\x11\x94\x00\x00\x00\x05\x04\x00\x00\x00" \
								"\x72\x00\x00\x00\x05\x04\x00\x00\x04\xbf\x00\x00\x00\x05\x04\x00" \
								"\x00\x03\x04\x00\x00\x00\x05\x04\x00\x00\x01\x71\x00\x00\x00\x05" \
								"\x04\x00\x00\x05\x08\x00\x00\x00\x05\x04\x00\x00\x01\x98\x00\x00" \
								"\x00\x05\x04\x00\x00\x11\xcc\x00\x00\x00\x05\x04\x00\x00\x05\x10" \
								"\x00\x00\x00\x05\x04\x00\x00\x11\xae\x00\x00\x00\x05\x04\x00\x00" \
								"\x01\xfc\x00\x00\x00\x05\x04\x00\x00\x03|\x00\x00\x00\x05" \
								"\x04\x00\x00\x05\x91\x00\x00\x00\x05\x04\x00\x00\x03\xc5\x00\x00" \
								"\x00\x05\x04\x00\x00\x08\x70\x00\x00\x00\x05\x04\x00\x00\x07\x90" \
								"\x00\x00\x00\x05\x04\x00\x00\x09q\x00\x00\x00\x05\x04\x00\x00" \
								"\x02\x84\x00\x00\x00\x05\x04\x00\x00\x00\xa5\x00\x00\x00\x05" \
								"\x04\x00\x00\x06\xf3\x00\x00\x00\x05\x04\x00\x00\x06\x84\x00" \
								"\x00\x00\x05\x04\x00\x00\x11\x71\x00\x00\x00\x05\x04\x00\x00\x10" \
								"\x42\x00\x00\x00\x05\x04\x00\x00\x03\xb4"
		test_stream_processor = StreamProcessor()
		test_stream_processor.handshake_occurred = True
		test_stream_processor.parse_stream(test_recursive_stream)

