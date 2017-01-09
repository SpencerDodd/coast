from twisted.internet.protocol import Protocol, ClientFactory

from messages import Handshake
from messages import Message

"""
This file defines the coast TCP implementation of the BitTorrent protocol in interacting with
peers
"""


class PeerProtocol(Protocol):
	def __init__(self, factory, peer):
		self.factory = factory
		self.peer = peer
		self.handshake_exchanged = False

	def connectionMade(self):
		print ("Connection made to peer ({}:{})".format(self.peer.ip, self.peer.port))
		print ("Sending handshake: {}".format(self.factory.torrent.get_handshake()))

		self.transport.write(self.factory.torrent.get_handshake())

	def dataReceived(self, data):

		if not self.handshake_exchanged:
			try:
				peer_shake = Handshake(data=data)
				self.handshake_exchanged = True
				self.peer.peer_id = peer_shake.peer_id
				print ("Handshake exchange with peer <||{}||> ip: {} port: {}".format(
					self.peer.peer_id, self.peer.ip, self.peer.port
				))
				print peer_shake.debug_values()
			except Exception as e:
				print ("Handshake failure: {}".format(e.message))

		else:
			self.process_message(data)

	def process_message(self, data):
		new_message = Message(data)
		print ("Non-handshake message:\n{}".format(new_message.debug_values()))

		# process the message based on the message_id of new_message
		# bitfield message: set the payload of the message to the bitfield of the peer


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

	def clientConnectionFailed(self, connector, reason):
		print ("Connection failed to peer ({}:{}): {}".format(self.peer.ip, self.peer.port, reason))
