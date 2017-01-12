import os
import hashlib
import unittest
from constants import CLIENT_ID_STRING, CURRENT_VERSION

"""
This is the core of the torrent client.
"""


class Core:
	def __init__(self):
		"""
		Dictionary of active torrents
		
		Key value is the name of the torrent file
		Value is a Torrent object
		"""
		self._active_torrents = {}
		self._peer_id = self.generate_peer_id()

	def generate_peer_id(self):
		"""
		Outputs a unique 20-byte urlencoded string used as the client identifier
		Uses Azureus-style encoding:
			'-' + (2-char client ID ascii) + (4-char integer version number) + '-'
		"""
		seed_string = "{}{}{}".format(os.getpgid(0), os.getcwd(), os.getlogin())
		pre_versioned_peer_id = hashlib.sha1(seed_string).hexdigest()
		peer_id_sub = pre_versioned_peer_id[28:]
		
		return "-{}{}-{}".format(CLIENT_ID_STRING,CURRENT_VERSION,peer_id_sub)
