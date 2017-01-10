import os
import hashlib

"""
This class represents a piece of a torrent downloaded from a peer.
"""


class Piece:
	def __init__(self, piece_length, index, hash, download_location, data=None):
		self.piece_length = piece_length
		self.index = index
		self.hash = hash
		self.temp_location = os.path.join(download_location, "tmp", "{}.piece".format(str(self.index)))
		self.data = data
		self.is_complete = False

		self.print_initialization()

	def print_initialization(self):
		pass

		output_string = "Creating new piece from:" + \
			"STRING" + \
			"\n\tpiece_len: {}".format(self.piece_length) + \
			"\n\tindex: {}".format(self.index) + \
			"\n\thash (bytes = {}): {}".format(len(self.hash), self.hash) + \
			"\n\ttemp_location = {}".format(self.temp_location) + \
			"\n\tdata: {}".format(self.data)

		print (output_string)

	def write_to_temporary_storage(self):
		if not self.is_complete:
			raise Exception("Trying to write incomplete piece to disk")

		# else
		with open(self.temp_location, "wb") as temp_location:
			temp_location.write(self.data)

		# delete data from piece to conserve program memory
		self.data = None

	# TODO:: Need to keep in mind that blocks inside the piece can be requested out of order.
	# TODO::
	def append_data(self, data):
		if len(self.data) + len(data) > self.piece_length:
			print ("Cannot append data to piece ({}). Overflow".format(self.index))
		else:
			self.data += data
			if len(self.data) == self.piece_length:
				self.is_complete = True

	def data_matches_hash(self):
		return hashlib.sha1(self.data) == self.hash
