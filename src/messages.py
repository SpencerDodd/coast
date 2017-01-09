import unittest

from helpermethods import convert_int_to_hex

"""
Representation of a handshake that is exchanged between the client and peers. Has two init
methods. One for creating a client handshake message to send to peers, and the other to handle
incoming peer handshakes into parsed and usable data by the client.
"""


class Handshake:
	def __init__(self, info_hash=None, peer_id=None, data=None):
		if data is None:
			self.pstrlen = convert_int_to_hex(19)
			self.pstr = "BitTorrent protocol"
			self.reserved = "\x00\x00\x00\x00\x00\x00\x00\x00"
			self.info_hash = info_hash
			self.peer_id = peer_id
		else:
			self.pstrlen = data[0]
			self.pstr = data[1:20]
			self.reserved = data[20:28]
			self.info_hash = data[28:48]
			self.peer_id = data[48:68]
			self.leftover_data = self.parse_remaining_messages(data[68:])

	def parse_remaining_messages(self, data):
		"""
		Returns an array of any remaining messages that followed the handshake sent by the
		peer in the same TCP frame.

		:param data: bytestream of TCP data that followed the handshake message
		:return: array of messages that followed the handshake in the same TCP message
		"""
		messages = []
		remaining_data = data

		while remaining_data:
			current_message = Message(data=remaining_data)
			remaining_data = current_message.leftover_data
			messages.append(current_message)

		return messages

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
		return "HANDSHAKE\n\tpstrlen:{}\n\tpstr:{}\n\tres:{}\n\tinfo:{}\n\tpeer:{}\n\textra:{}".format(
			ord(self.pstrlen),
			self.pstr,
			self.reserved,
			self.info_hash,
			self.peer_id,
			self.format_messages(self.leftover_data))

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
		if len(data) == 0:
			print ("No data given to Message constructor")
		else:
			self.len_prefix = int("".join(str(ord(c)) for c in data[0:4]))
			self.message_id = str(ord(data[4]))
			self.payload = data[5:self.len_prefix]
			self.leftover_data = data[self.len_prefix:]

	def debug_values(self):
		"""
		Returns string of the message's variable data
		:return: string
		"""
		return "MESSAGE:\n\tlen_prefix:{}\n\tmessage_id:{}\n\tpayload:{}\n\tleftover:{}".format(
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