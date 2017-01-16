from twisted.internet.protocol import Protocol, ClientFactory
from twisted.python.failure import Failure
from peer import Peer
from messages import StreamProcessor

"""
This file defines the coast TCP implementation of the BitTorrent protocol in interacting with
peers
"""


class PeerProtocol(Protocol):
	def __init__(self, factory, peer):
		self.factory = factory
		self.peer = peer
		self.handshake_exchanged = False
		self.stream_processor = StreamProcessor(self.factory.torrent)
		self.outgoing_messages = []

	def connectionMade(self):
		print ("Connection made to peer ({}:{})".format(self.peer.ip, self.peer.port))
		print ("Sending handshake: {}".format(self.factory.torrent.get_handshake()))

		self.transport.write(self.factory.torrent.get_handshake())

	def dataReceived(self, data):
		self.process_stream(data)
		self.send_next_messages()

	def process_stream(self, data):
		# TODO: mechanism for dropping garbage data.
		self.stream_processor.parse_stream(data)
		self.peer.received_messages(self.stream_processor.get_complete_messages())

		# purge the completed messages
		self.stream_processor.purge_complete_messages()

	def send_next_messages(self):
		"""Performs any actions as defined in the actions queue `self.client_actions` which is
		a stack of a method, a peer, and a complete message which are messages from the peer
		to be executed by the client. It also sends any messages to the peer from the client
		following client execution of peer messages that are found in the actions queue
		`self.client_responses`. This action queue is populated by ..."""

		"""
		If handshaking has occurred, check to see if the given matches the torrent. If not,
		terminate the connection
		"""
		if self.handshake_exchanged:
			if self.peer.info_hash != self.factory.torrent.generate_hex_info_hash():
				self.connectionLost(reason=Failure("Peer info hash did not match torrent info hash"))

		print ("Checking on Torrent to see how to proceed")
		self.factory.torrent.process_next_round(self.peer)

		# we get our next messages from peer
		self.outgoing_messages += self.peer.get_next_messages()

		# send them and update the last time of contact for the peer (for keep-alive)
		for outgoing_message in self.outgoing_messages:
			print ("Sending message: {}".format(str(outgoing_message)))

			self.transport.write(outgoing_message.message())
			self.peer.update_last_contact()

		self.outgoing_messages = []


class PeerFactory(ClientFactory):
	def __init__(self, torrent, peer):
		self.torrent = torrent
		self.protocols = []
		self.peer = peer

	def startedConnecting(self, connector):
		print ("Starting connection to peer ({}: {})".format(self.peer.ip, self.peer.port))

	def buildProtocol(self, addr):
		protocol = PeerProtocol(self, self.peer)
		self.protocols.append(protocol)
		return protocol

	def clientConnectionLost(self, connector, reason):
		print ("Lost connection to peer ({}:{}): {}".format(self.peer.ip, self.peer.port, reason))
		self.torrent.remove_active_peer(self.peer)

	def clientConnectionFailed(self, connector, reason):
		print ("Connection failed to peer ({}:{}): {}".format(self.peer.ip, self.peer.port, reason))
