import os
import bencode
import unittest
import traceback
from auxillarymethods import one_directory_back

"""
This class represents a torrent. It holds information (metadata) about the torrent
as parsed from the .torrent file. Additionally it holds information about the
progress of download, hosts in swarm, 
"""
class Torrent:

	def __init__(self):
		# essential content
		self.info = None
		self.announce = None
		# optional content
		self.announce_list = None
		self.creation_date = None
		self.comment = None
		self.created_by = None
		self.encoding = None

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
					self.announce = decoded_data["announce"]
					self.info = decoded_data["info"]
					# fill in our optional fields if they exist
					meta_keys = decoded_data.keys()
					if "announce-list" in meta_keys:
						self.announce_list = decoded_data["announce-list"]
					if "creation date" in meta_keys:
						self.creation_date = decoded_data["creation date"]
					if "comment" in meta_keys:
						self.comment = decoded_data["comment"]
					if "created by" in meta_keys:
						self.created_by = decoded_data["created by"]
					if "encoding" in meta_keys:
						self.encoding = decoded_data["encoding"]

			except Exception as e:
				error_message = "File is improperly formatted\n{}".format(traceback.format_exc(e))
				raise ValueError(error_message)


		else:
			raise ValueError("File is not .torrent type")


class TestTorrent(unittest.TestCase):
	
	def test_metadate_from_file(self):
		test_torrent = Torrent()
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test_data/")
		torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent.initialize_metadata_from_file(os.path.join(test_data_directory,torrent_file))


if __name__ == "__main__":
	unittest.main()























