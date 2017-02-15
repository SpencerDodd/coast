import os
import hashlib

from constants import REQUEST_SIZE, DOWNLOAD_BAR_LEN
from helpermethods import format_hex_output

"""
This class represents a piece of a torrent downloaded from a peer.
"""


class Piece:
	def __init__(self, piece_length, index, hash, download_location):
		self.piece_length = piece_length
		self.index = index
		self.hash = hash
		self.temp_location = os.path.join(download_location, "tmp", "{}.piece".format(str(self.index).zfill(8)))
		self.data = []
		self.progress = 0.0
		self.is_complete = False
		self.completed_request_indices = []
		self.non_completed_request_indices = []

		for x in range(0, self.piece_length):
			self.data.append(0)
		# DEBUG
		# self.debug_string()

	def debug_values(self):

		output_string = "PIECE" + \
			"\npiece_len: {}".format(self.piece_length) + \
			"\nindex: {}".format(self.index) + \
			"\nhash (bytes = {}): {}".format(len(self.hash), self.hash) + \
			"\ntemp_location = {}".format(self.temp_location) + \
			"\nprogress = {}".format(self.progress) + \
			"\ndownloaded data: (bytes = {})".format(len([val for val in self.data if val != 0]))

		return (output_string)

	def get_next_begin(self):
		"""
		Gets the next index for a request to be sent to a remote peer for download
		:return: int representing index to be requested
		"""
		# TODO: does assume sequential download of blocks
		# 		i.e. all blocks before the next have all been downloaded or requested for
		if len(self.non_completed_request_indices + self.completed_request_indices) > 0:
			return max(self.non_completed_request_indices + self.completed_request_indices) + REQUEST_SIZE
		else:
			return 0

	def write_to_temporary_storage(self):
		if self.is_complete:
			with open(self.temp_location, "w") as temp_file:
				for datum in self.data:
					temp_file.write(datum)

	def update_progress(self):
		self.progress = ((len(self.data) - self.data.count(0)) / float(len(self.data))) * 100

		if int(self.progress) == 100:
			self.is_complete = True

	def add_non_completed_request_index(self, request_message):
		self.non_completed_request_indices.append(int(request_message.get_begin()))

	def append_data(self, piece_message):
		# DEBUG

		# print ("appending data")
		# print ("block index: {}".format(piece_message.get_begin()))
		# print ("completed indices: {}".format(",".join(str(a) for a in self.completed_request_indices)))
		# print ("non-completed indices: {}".format(",".join(str(a) for a in self.non_completed_request_indices)))

		for x in range(0, len(piece_message.block)):
			self.data[piece_message.get_begin() + x] = piece_message.block[x]

		self.completed_request_indices.append(piece_message.get_begin())
		self.non_completed_request_indices.remove(int(piece_message.get_begin()))
		self.update_progress()

		# DEBUG
		# print ("completed indices: {}".format(",".join(str(a) for a in self.completed_request_indices)))
		# print ("non-completed indices: {}".format(",".join(str(a) for a in self.non_completed_request_indices)))

	def non_completed_request_exists(self, request_message):
		return request_message.get_begin() in self.non_completed_request_indices

	def data_matches_hash(self):
		current_hash = hashlib.sha1("".join(byte for byte in self.data)).digest()
		# DEBUG
		# print ("Comparing hashes for completed piece")
		# print ("Current hash: {}".format(format_hex_output(current_hash)))
		# print ("Piece hash:   {}".format(format_hex_output(self.hash)))
		# print ("Same? {}".format(current_hash == self.hash))
		return current_hash == self.hash

	def progress_string(self):
		bars_to_render = int((self.progress / 100.0) * DOWNLOAD_BAR_LEN)
		return u"{}% {}".format(str(self.progress).rjust(6), bars_to_render * u'\u2588')

	def get_index(self):
		return self.index

	def reset(self):
		self.data = []
		self.progress = 0.0
		self.is_complete = False
		self.completed_request_indices = []
		self.non_completed_request_indices = []
