"""
Constants used across the project
"""
PROTOCOL_STRING = "BitTorrent protocol"
ERROR_BYTESTRING_CHUNKSIZE = "Input not divisible by chunk size"
MAX_PEERS = 1
MESSAGE_ID = {
	0: "choke",
	1: "unchoke",
	2: "interested",
	3: "not interested",
	4: "have",
	5: "bitfield",
	6: "request",
	7: "piece",
	8: "cancel",
	9: "port"
}