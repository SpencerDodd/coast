import unittest
from coast.bencode import bdecode, BTFailure


class TestBencode(unittest.TestCase):
	def test_int(self):
		self.assertEqual(1, bdecode("i1e"))
		self.assertEqual(-1, bdecode("i-1e"))
		self.assertEqual(100, bdecode("i100e"))

		# Error raising
		with self.assertRaises(BTFailure) as context:
			bdecode("i10ae")

	def test_string(self):
		self.assertEqual("", bdecode("0:"))
		self.assertEqual("test", bdecode("4:test"))
		self.assertEqual("holy guacamole", bdecode("14:holy guacamole"))
		with self.assertRaises(BTFailure) as context:
			bdecode("3:test")
		with self.assertRaises(BTFailure) as context:
			bdecode("5:test")

	def test_list(self):
		self.assertEqual([1, 2, 3, 4], bdecode("li1ei2ei3ei4ee"))
		self.assertEqual([1, "a", 2, "b"], bdecode("li1e1:ai2e1:be"))
		self.assertEqual([1, [2, 3, 4]], bdecode("li1eli2ei3ei4eee"))
		self.assertEqual(["test", "list"], bdecode("l4:test4:liste"))

	def test_dict(self):
		self.assertEqual({"key": "value"}, bdecode("d3:key5:valuee"))
		self.assertEqual({"key": 1}, bdecode("d3:keyi1ee"))
		self.assertEqual({"key": ["list"]}, bdecode("d3:keyl4:listee"))
		self.assertEqual({"key": ["list", 1]}, bdecode("d3:keyl4:listi1eee"))


if __name__ == "__main__":
	unittest.main()