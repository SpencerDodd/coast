"""
Constants used across the project
"""

PROTOCOL_STRING = "BitTorrent protocol"
ERROR_BYTESTRING_CHUNKSIZE = "Input not divisible by chunk size"
MAX_PEERS = 40
REQUEST_SIZE = 16384	 			# 16kb (deluge default)
MAX_OUTSTANDING_REQUESTS = 10		# set to 10-15 in production
PEER_INACTIVITY_LIMIT = 30			# set to 60-120 (seconds) in production

# Client information
CLIENT_ID_STRING = "CO"
CURRENT_VERSION = "0001"

# Networking
RUNNING_PORT = 6881
LISTENING_PORT_MIN = 6881
LISTENING_PORT_MAX = 6889
RESPONSE_TIMEOUT = 5

# Formatting
DOWNLOAD_BAR_LEN = 20

# Activity
ACTIVITY_INITIALIZE_NEW = 			0
ACTIVITY_INITIALIZE_CONTINUE = 		1
ACTIVITY_DOWNLOADING = 				2
ACTIVITY_STOPPED = 					3
ACTIVITY_COMPLETED = 				4

# Debugging
DEBUG = True
