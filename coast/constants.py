"""
Constants used across the project
"""

PROTOCOL_STRING = "BitTorrent protocol"
ERROR_BYTESTRING_CHUNKSIZE = "Input not divisible by chunk size"
MAX_PEERS = 50
REQUEST_SIZE = 16384	 			# 16kb (deluge default)
MAX_OUTSTANDING_REQUESTS = 5 		# set to 10-15 in production

# Client information
CLIENT_ID_STRING = "CO"
CURRENT_VERSION = "0001"

# Networking
LISTENING_PORT_MIN = 6881
LISTENING_PORT_MAX = 6889