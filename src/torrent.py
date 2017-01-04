import re
import os
import time
import urllib
import bencode
import hashlib
import requests
import unittest
import traceback
from auxillarymethods import one_directory_back

from peer import Peer

# Error messages
ERROR_BYTESTRING_CHUNKSIZE = "Input not divisible by chunk size"

"""
This class represents a torrent. It holds information (metadata) about the torrent
as parsed from the .torrent file.
"""
class Torrent:

	def __init__(self):
		"""
		Metadata fields
		"""
		# essential content
		self._info = None								# dictionary
		self._announce = None							# string
		"""
		Tracker request fields
		"""
		self.tracker_request = {
			"info_hash":None,
			"peer_id":None,
			"port":None,
			"uploaded":0,
			"downloaded":0,
			"left":None,
			"compact":0,
			"no_peer_id":0,
			"event":"started",
			"ip":None,
			"numwant":200,
			"key":None,
			"trackerid":None
		}

		"""
		Tracker response fields
		"""
		self.tracker_response = {
			"failure reason":None,
			"warning message":None,
			"interval":None,
			"min interval":None,
			"tracker id":None,
			"complete":None,
			"incomplete":None,
			"peers":None,
		}

		"""
		Status fields for the torrent
		"""
		self.last_request = None
		self.last_announce = None
		self.metadata_initialized = False
		self.event_set = False
		self.last_response_object = None

		"""
		Data fields
		"""
		self.peers = []

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

				self.metadata_initialized = True

			except Exception as e:
				error_message = "File is improperly formatted\n{}".format(traceback.format_exc(e))
				raise ValueError(error_message)


		else:
			raise ValueError("File is not .torrent type")

	"""
	Initializes the torrent for requests to the tracker
	"""
	def intialize_for_tracker_requests(self, peer_id, port):
		if self.metadata_initialized:
			self.tracker_request["peer_id"] = peer_id
			self.tracker_request["port"] = port
			self.tracker_request["info_hash"] = self.generate_info_hash()
			self.tracker_request["left"] = self._info["length"]
		else:
			raise AttributeError("Torrent metadata not initialized")

	"""
	Returns true if the torrent can make an announce request

	Relevant standards information / response fields:
	---------------------------------------------------------------------------
	interval: Interval in seconds that the client should wait between sending 
		regular requests to the tracker
	min interval: (optional) Minimum announce interval. If present clients must
		not reannounce more frequently than this.
	---------------------------------------------------------------------------
	"""
	def can_request(self):
		if self.last_request is not None:
			time_since_request = time.time() - self.last_request

			if self.tracker_response["interval"] is None:
				return True

			elif time_since_request > self.tracker_response["interval"]:
				return True

			else:
				return False
		else:
			return True

	"""
	Generates an ascii hash of the bencoded info dict
	"""
	def generate_ascii_info_hash(self):
		bencoded_info_dict = bencode.bencode(self._info)
		return hashlib.sha1(bencoded_info_dict).hexdigest()
	"""
	Generates a hex hash of the bencoded info dict
	"""
	def generate_hex_info_hash(self):
		bencoded_info_dict = bencode.bencode(self._info)
		return hashlib.sha1(bencoded_info_dict).digest()

	"""
	Generates the final URL-encoded hash of the hex hash of the bencoded info
	dict.

	Reserves RFC unreserved characters -_.!~*'()
	"""
	def generate_info_hash(self):
		sha1_hash = self.generate_hex_info_hash()
		url_encoded_hash = urllib.quote(sha1_hash, safe="-_.!~*'()")
		return url_encoded_hash

	"""
	Return a string representing a request to make to the torrent's tracker.
	This request is handled by the NetworkHandler.

	The tracker is an HTTP/HTTPS service which responds to HTTP GET requests. 
	The requests include metrics from clients that help the tracker keep 
	overall statistics about the torrent. The response includes a peer list 
	that helps the client participate in the torrent. The base URL consists 
	of the "announce URL" as defined in the metainfo (.torrent) file. The 
	parameters are then added to this URL, using standard CGI methods (i.e. 
	a '?' after the announce URL, followed by 'param=value' sequences separated 
	by '&').

	Parameters used in the client->tracker GET are as follows:
	(From the unofficial spec: https://wiki.theory.org/BitTorrentSpecification)

		info_hash: urlencoded 20-byte SHA1 hash of the value of the info key 
			from the Metainfo file. Note that the value will be a bencoded 
			dictionary, given the definition of the info key above.

		peer_id: urlencoded 20-byte string used as a unique ID for the client, 
			generated by the client at startup. This is allowed to be any 
			value, and may be binary data. There are currently no guidelines 
			for generating this peer ID. However, one may rightly presume that 
			it must at least be unique for your local machine, thus should 
			probably incorporate things like process ID and perhaps a 
			timestamp recorded at startup. See peer_id below for common client 
			encodings of this field.

		port: The port number that the client is listening on. Ports reserved 
			for BitTorrent are typically 6881-6889. Clients may choose to give 
			up if it cannot establish a port within this range.

		uploaded: The total amount uploaded (since the client sent the 
			'started' event to the tracker) in base ten ASCII. While not 
			explicitly stated in the official specification, the concensus is 
			that this should be the total number of bytes uploaded.

		downloaded: The total amount downloaded (since the client sent the 
			'started' event to the tracker) in base ten ASCII. While not 
			explicitly stated in the official specification, the consensus is 
			that this should be the total number of bytes downloaded.

		left: The number of bytes this client still has to download in base 
			ten ASCII. Clarification: The number of bytes needed to download to
			be 100% complete and get all the included files in the torrent.

		compact: Setting this to 1 indicates that the client accepts a compact 
			response. The peers list is replaced by a peers string with 6 bytes
			per peer. The first four bytes are the host (in network byte order)
			, the last two bytes are the port (again in network byte order). 
			It should be noted that some trackers only support compact 
			responses (for saving bandwidth) and either refuse requests 
			without "compact=1" or simply send a compact response unless the 
			request contains "compact=0" (in which case they will refuse the 
			request.)

		no_peer_id: Indicates that the tracker can omit peer id field in peers 
			dictionary. This option is ignored if compact is enabled.

		event: If specified, must be one of started, completed, stopped, (or
			empty which is the same as not being specified). If not specified, 
			then this request is one performed at regular intervals.
			`event` flags:
				started: The first request to the tracker must include the 
					event key with this value.
				stopped: Must be sent to the tracker if the client is shutting
					down gracefully.
				completed: Must be sent to the tracker when the download 
					completes. However, must not be sent if the download was 
					already 100% complete when the client started. Presumably,
					this is to allow the tracker to increment the "completed 
					downloads" metric based solely on this event.

		ip: Optional. The true IP address of the client machine, in dotted quad
			format or rfc3513 defined hexed IPv6 address. Notes: In general 
			this parameter is not necessary as the address of the client can 
			be determined from the IP address from which the HTTP request came.
			The parameter is only needed in the case where the IP address that
			the request came in on is not the IP address of the client. This 
			happens if the client is communicating to the tracker through a 
			proxy (or a transparent web proxy/cache.) It also is necessary when
			both the client and the tracker are on the same local side of a NAT
			gateway. The reason for this is that otherwise the tracker would 
			give out the internal (RFC1918) address of the client, which is not
			routable. Therefore the client must explicitly state its (external,
			routable) IP address to be given out to external peers. Various 
			trackers treat this parameter differently. Some only honor it only 
			if the IP address that the request came in on is in RFC1918 space. 
			Others honor it unconditionally, while others ignore it completely.
			In case of IPv6 address (e.g.: 2001:db8:1:2::100) it indicates only
			that client can communicate via IPv6.

		numwant: Optional. Number of peers that the client would like to 
			receive from the tracker. This value is permitted to be zero. If 
			omitted, typically defaults to 50 peers.

		key: Optional. An additional identification that is not shared with 
			any other peers. It is intended to allow a client to prove their 
			identity should their IP address change.

		trackerid: Optional. If a previous announce contained a tracker id, it 
			should be set here.
	"""

	def get_tracker_request(self):
		request_text = "{}?info_hash={}".format(self._announce, self.tracker_request["info_hash"])

		for request_field in self.tracker_request.keys():
			field_data = self.tracker_request[request_field]
			if request_field is not "info_hash" and field_data is not None:
				request_text += "&{}={}".format(request_field, field_data)

		return request_text

	"""
	input: String, output: void

	Updates the torrent based on a response from the tracker

	failure reason: If present, then no other keys may be present. The value is
		a human-readable error message as to why the request failed (string).
	warning message: (new, optional) Similar to failure reason, but the 
		response still gets processed normally. The warning message is shown 
		just like an error.
	interval: Interval in seconds that the client should wait between sending 
		regular requests to the tracker
	min interval: (optional) Minimum announce interval. If present clients must
		not reannounce more frequently than this.
	tracker id: A string that the client should send back on its next 
		announcements. If absent and a previous announce sent a tracker id, 
		do not discard the old value; keep using it.
	complete: number of peers with the entire file, i.e. seeders (integer)
	incomplete: number of non-seeder peers, aka "leechers" (integer)
	peers: (dictionary model) The value is a list of dictionaries, each with 
		the following keys:
	peer id: peer's self-selected ID, as described above for the tracker 
		request (string)
	ip: peer's IP address either IPv6 (hexed) or IPv4 (dotted quad) or DNS 
		name (string)
	port: peer's port number (integer)
	peers: (binary model) Instead of using the dictionary model described 
		above, the peers value may be a string consisting of multiples of 6 
		bytes. First 4 bytes are the IP address and last 2 bytes are the port 
		number. All in network (big endian) notation.
	"""
	def process_tracker_response(self, tracker_response):
		self.last_response_object = tracker_response
		response_text = tracker_response.text
		decoded_response = bencode.bdecode(response_text)
						
		for response_field in decoded_response.keys():
			self.tracker_response[response_field] = decoded_response[response_field]

		self.populate_peers()

	def get_last_response(self):
		return self.last_response_object

	"""
	Creates peer objects from the peer field (hex) of the response object
	from the tracker
	"""
	def populate_peers(self):
		if self.tracker_response["peers"] is None:
			raise Exception("Peers not populated (check tracker response)")

		else:
			chunked_peers = self.chunk_bytestring(self.tracker_response["peers"])
			for peer_chunk in chunked_peers:
				new_peer = Peer()
				new_peer.initialize_with_chunk(peer_chunk)
				self.peers.append(new_peer)

			print (":".join(str(ord(x)) for x in self.tracker_response["peers"]))

	"""
	Chunks a bytestring into an array of (default) 6-byte pieces

	Used for:
		parsing bytestring for peers into individual peers
	"""
	def chunk_bytestring(self, input, length=6):
		if len(input) % length != 0:
			raise Exception(ERROR_BYTESTRING_CHUNKSIZE)
		else:
			return [input[x:x+length] for x in range(0, len(input), length)]


"""
Tests
"""

class TestTorrent(unittest.TestCase):

	def test_urlencode_hash(self):
		test_sha1_hash = "0403fb4728bd788fbcb67e87d6feb241ef38c75a"
		text_hex_hash = "\x04\x03\xfbG(\xbdx\x8f\xbc\xb6~\x87\xd6\xfe\xb2A\xef8\xc7Z"
		expected_url_hash = "%04%03%FBG(%BDx%8F%BC%B6~%87%D6%FE%B2A%EF8%C7Z"

		self.assertEqual(expected_url_hash, urllib.quote(text_hex_hash, safe="-_.!~*'()"))
	
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
		expected_info_hash = "%04%03%FBG(%BDx%8F%BC%B6~%87%D6%FE%B2A%EF8%C7Z"
		#expected_info["pieces"] = (Omitted due to size and gibberish)

		self.assertEqual(expected_announce, test_torrent._announce)
		self.assertEqual(expected_announce_list, test_torrent._announce_list)
		self.assertEqual(expected_info["length"], test_torrent._info["length"])
		self.assertEqual(expected_info["name"], test_torrent._info["name"])
		self.assertEqual(expected_info["piece length"], test_torrent._info["piece length"])
		self.assertEqual(60800, len(test_torrent._info["pieces"]))
		self.assertEqual(expected_info_hash, test_torrent.generate_info_hash())

	def test_tracker_request(self):
		test_torrent = Torrent()
		root_dir = one_directory_back(os.getcwd())
		test_data_directory = os.path.join(root_dir, "test_data/")
		test_torrent_file = "ubuntu-16.10-desktop-amd64.iso.torrent"
		test_torrent.initialize_metadata_from_file(os.path.join(test_data_directory,test_torrent_file))

		peer_id = "-Co0001-7a673c102d18"
		port = 6881
		test_torrent.intialize_for_tracker_requests(peer_id, port)

		expected_request = "http://torrent.ubuntu.com:6969/announce?info_h" + \
		"ash=%04%03%FBG(%BDx%8F%BC%B6~%87%D6%FE%B2A%EF8%C7Z&uploaded=0&dow" + \
		"nloaded=0&event=started&compact=0&numwant=200&no_peer_id=0&port=6" + \
		"881&peer_id=-Co0001-7a673c102d18&left=1593835520"

		deluge_request = "http://torrent.ubuntu.com:6969/announce?info_has" + \
		"h=%04%03%FBG(%BDx%8F%BC%B6~%87%D6%FE%B2A%EF8%C7Z&peer_id=-DE13D0-" + \
		"3qXsknyO08~0&port=55434&uploaded=0&downloaded=7189540&left=5504&c" + \
		"orrupt=0&key=7BF44946&event=stopped&numwant=0&compact=1&no_peer_i" + \
		"d=1&supportcrypto=1&redundant=0"

		self.assertEqual(expected_request, test_torrent.get_tracker_request())

	def test_chunk_bytestring(self):
		test_peer_chunk = u"N\xe6\xcd2\xc5DN\xe6\xcd2\xc5D"
		test_torrent = Torrent()
		expected_chunks = 2

		self.assertEqual(expected_chunks, len(test_torrent.chunk_bytestring(test_peer_chunk)))

		test_broken_chunk = u"N\xe6\xcd2\xc5DN\xe6\xcd2\xc5De"
		with self.assertRaises(Exception) as context:
			test_torrent.chunk_bytestring(test_broken_chunk)
		self.assertTrue(ERROR_BYTESTRING_CHUNKSIZE in context.exception)

	def test_populate_peers(self):
		pass

if __name__ == "__main__":
	unittest.main()





















