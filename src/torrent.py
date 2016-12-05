import os
import bencode
import unittest
import traceback
from auxillarymethods import one_directory_back

"""
This class represents a torrent. It holds information (metadata) about the torrent
as parsed from the .torrent file.
"""
class Torrent:

	def __init__(self):
		# essential content
		self._info = None
		self._announce = None
		# optional content
		self._announce_list = None
		self._creation_date = None
		self._comment = None
		self._created_by = None
		self._encoding = None

	"""
	Fills in torrent information by reading from a metadata file (.torrent)
	"""
	def initialize_metadata_from_file(self, metadata_file_path):
		# check if we have a torrent file
		if ".torrent" == metadata_file_path[-8:]:
			try:
				with open(metadata_file_path, "r") as metadata_file:
					metadata = metadata_file.read()
					decoded_data = bencode.bdecode(metadata)

					# fill in our essential fields
					self._announce = decoded_data["announce"]
					self._info = decoded_data["info"]
					# fill in our optional fields if they exist
					meta_keys = decoded_data.keys()
					if "announce-list" in meta_keys:
						self._announce_list = decoded_data["announce-list"]
					if "creation date" in meta_keys:
						self._creation_date = decoded_data["creation date"]
					if "comment" in meta_keys:
						self._comment = decoded_data["comment"]
					if "created by" in meta_keys:
						self._created_by = decoded_data["created by"]
					if "encoding" in meta_keys:
						self._encoding = decoded_data["encoding"]

			except Exception as e:
				error_message = "File is improperly formatted\n{}".format(traceback.format_exc(e))
				raise ValueError(error_message)


		else:
			raise ValueError("File is not .torrent type")


class TestTorrent(unittest.TestCase):
	"""
	d8:announce44:http://torrent.testtorrent.com:6969/announce13:announce-listll44:http://torrent.testtorrent.com:6969/announceel50:http://ipv6.torrent.testtorrent.com:6969/announceee7:comment12:Test Torrent13:creation datei1476352188e4:infod6:lengthi1593835520e4:name28:test-torrent.iso.mp3.avi.exe12:piece lengthi1337e6:pieces4:testee
	"""
	
	def test_metadate_from_file(self):
		test_torrent = Torrent()
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test_data/")
		test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent.initialize_metadata_from_file(os.path.join(test_data_directory,test_torrent_file))

		expected_announce = "http://torrent.ubuntu.com:6969/announce"
		expected_announce_list = [
			["http://torrent.ubuntu.com:6969/announce"],
			["http://ipv6.torrent.ubuntu.com:6969/announce"]
		]
		expected_info = {}
		
		expected_info["length"] = 1593835520
		expected_info["name"] = "ubuntu-16.10-desktop-amd64.iso"
		expected_info["piece length"] = 524288
		#expected_info["pieces"] = (Omitted due to size and gibberish)

		self.assertEqual(expected_announce, test_torrent._announce)
		self.assertEqual(expected_announce_list, test_torrent._announce_list)
		self.assertEqual(expected_info["length"], test_torrent._info["length"])
		self.assertEqual(expected_info["name"], test_torrent._info["name"])
		self.assertEqual(expected_info["piece length"], test_torrent._info["piece length"])
		self.assertEqual(60800, len(test_torrent._info["pieces"]))

if __name__ == "__main__":
	unittest.main()























