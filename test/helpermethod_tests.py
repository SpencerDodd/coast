import unittest
from coast.helpermethods import convert_int_to_hex, convert_hex_to_int, format_hex_output


class HelpermethodTests(unittest.TestCase):
	def test_convert_int_to_hex(self):
		self.assertEqual("\x00\x00\x40\x00", convert_int_to_hex(16384, 4))

	def test_convert_hex_to_int(self):
		self.assertEqual(16384, convert_hex_to_int("\x00\x00\x40\x00"))

	def test_format_hex(self):
		self.assertEqual("0x41 0x41 0x41 0x41", format_hex_output("\x41\x41\x41\x41"))