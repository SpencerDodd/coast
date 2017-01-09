from twisted.internet.protocol import Protocol, ClientFactory

from peer import Peer
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
		self.MESSAGE_ID = {
			"0": Peer.process_choke,
			"1": Peer.process_unchoke,
			"2": Peer.process_interested,
			"3": Peer.process_not_interested,
			"4": Peer.process_have,
			"5": Peer.process_bitfield,
			"6": Peer.process_request,
			"7": Peer.process_piece,
			"8": Peer.process_cancel,
			"9": Peer.process_port
		}
		self.actions = []

	def connectionMade(self):
		print ("Connection made to peer ({}:{})".format(self.peer.ip, self.peer.port))
		print ("Sending handshake: {}".format(self.factory.torrent.get_handshake()))

		self.transport.write(self.factory.torrent.get_handshake())

	def dataReceived(self, data):
		# TODO:: this should all be moved inside of self.process_stream()
		if not self.handshake_exchanged:
			try:
				peer_shake = Handshake(data=data)
				self.handshake_exchanged = True
				self.peer.peer_id = peer_shake.peer_id
				print ("Handshake exchange with peer <||{}||> ip: {} port: {}".format(
					self.peer.peer_id, self.peer.ip, self.peer.port
				))
				print peer_shake.debug_values()

				# TODO:: what to do with partial messages appended to handshake frame

			except Exception as e:
				print ("Handshake failure: {}".format(e.message))

		else:
			self.process_stream(data)
			self.perform_actions_if_required()

	def process_stream(self, data):
		# TODO:: this only works if all messages are sent in frame. Need to employ a stream
		# TODO::	stack that parses messages out of the stream and holds the last partially
		# TODO::	filled message for the next received message. Also needs to perform checks
		# TODO::	to ensure that the next packet stream contains valid data for that message

		new_message = Message(data)
		print ("Non-handshake message:\n{}".format(new_message.debug_values()))

		# process the message based on the message_id of new_message
		action = self.MESSAGE_ID[new_message.message_id]
		action(self.peer, new_message)

	def perform_actions_if_required(self):
		# TODO:: performs any actions as defined in the actions queue `self.actions` which is
		# TODO::	a stack of a method, a peer, and a complete message.
		for action in self.actions:
			method = action[0]
			peer = action[1]
			message = action[2]

			method(peer, message)


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
