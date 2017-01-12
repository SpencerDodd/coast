import unittest
from coast.core import Core


class TestClient(unittest.TestCase):
	def test_peer_id_generation(self):
		test_client = Core()
		test_client.generate_peer_id()
		self.assertEquals(20, len(test_client._peer_id))

if __name__ == "__main__":
	unittest.main()

