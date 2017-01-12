import os
import hashlib

"""
This class represents a piece of a torrent downloaded from a peer.
"""


class Piece:
	def __init__(self, piece_length, index, hash, download_location):
		self.piece_length = piece_length
		self.index = index
		self.hash = hash
		self.temp_location = os.path.join(download_location, "tmp", "{}.piece".format(str(self.index)))
		self.data = []
		self.progress = 0.0
		self.is_complete = False

		for x in range(0, self.piece_length):
			self.data.append(0)
		# self.debug_string()

	def debug_string(self):

		output_string = "Creating new piece from:" + \
			"STRING" + \
			"\n\tpiece_len: {}".format(self.piece_length) + \
			"\n\tindex: {}".format(self.index) + \
			"\n\thash (bytes = {}): {}".format(len(self.hash), self.hash) + \
			"\n\ttemp_location = {}".format(self.temp_location) + \
			"\n\tprogress = {}".format(self.progress) + \
			"\n\tdata: {}".format(self.data)

		print (output_string)

	def get_next_begin(self):
		"""
		Gets the next index for a request to be sent to a remote peer for download
		:return: int representing index to be requested
		"""
		return self.data.index(0)

	def write_to_temporary_storage(self):
		if not self.is_complete:
			raise Exception("Trying to write incomplete piece to disk")

		# else
		with open(self.temp_location, "wb") as temp_location:
			temp_location.write(self.data)

		# delete data from piece to conserve program memory
		self.data = None

	def update_progress(self):
		self.progress = ((len(self.data) - self.data.count(0)) / float(len(self.data))) * 100

		if int(self.progress) == 100: # TODO: ensure conversion isn't dangerous
			self.is_complete = True

	def append_data(self, piece_message):
		for x in range(0, len(piece_message.block)):
			self.data[piece_message.index + x] = piece_message.block[x]

		self.update_progress()

	def data_matches_hash(self):
		return hashlib.sha1(self.data) == self.hash
