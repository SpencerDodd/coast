from twisted.internet.protocol import Protocol, ClientFactory

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
			"9": Peer.process_port,
			"20": Peer.process_extended_handshake
		}
		self.stream_processor = StreamProcessor()
		self.received_message_actions = []
		self.outgoing_messages = []

	def connectionMade(self):
		print ("Connection made to peer ({}:{})".format(self.peer.ip, self.peer.port))
		print ("Sending handshake: {}".format(self.factory.torrent.get_handshake()))

		self.transport.write(self.factory.torrent.get_handshake())

	def dataReceived(self, data):
		self.process_stream(data)
		self.perform_actions_if_required()

	def process_stream(self, data):
		# TODO:: first message after handshake should be `InterestedMessage` if we are indeed
		# 			interested in what the peer has (check client pieces?)
		self.stream_processor.parse_stream(data)
		complete_messages = self.stream_processor.complete_messages

		for message in complete_messages:
			# print ("Message:\n{}".format(message.debug_values()))
			if message.message_type == "Handshake":
				self.peer.peer_id = message.peer_id
				print ("Handshake exchange with peer <||{}||> ip: {} port: {}".format(
					self.peer.peer_id, self.peer.ip, self.peer.port
				))

			else:
				# add complete messages as actions for the peer
				self.received_message_actions.append([
					self.MESSAGE_ID[message.message_id],
					self.peer,
					message]
				)

		if self.stream_processor.final_incomplete_message is not None:
			print ("Incomplete: {}".format(self.stream_processor.final_incomplete_message.debug_values()))

		# purge the completed messages
		self.stream_processor.purge_complete_messages()

	def perform_actions_if_required(self):
		"""Performs any actions as defined in the actions queue `self.client_actions` which is
		a stack of a method, a peer, and a complete message which are messages from the peer
		to be executed by the client. It also sends any messages to the peer from the client
		following client execution of peer messages that are found in the actions queue
		`self.client_responses`. This action queue is populated by ..."""
		# TODO:: figure out message response flow and the interaction between torrent and peer
		# 			in establishing what pieces to request from peer.
		print ("Processing received messages in Peer")
		for action in self.received_message_actions:
			method = action[0]
			peer = action[1]
			message = action[2]

			method(peer, message)

		# TODO:: figure out how the form of client responses and how to act on them
		print ("Checking on Torrent to see how to proceed")
		self.factory.torrent.process_next_round(self.peer)

		# we get our next messages from peer
		self.outgoing_messages += self.peer.get_next_messages()

		# send them and update the last time of contact for the peer (for keep-alive)
		print ("outgoing: {}".format(self.outgoing_messages))
		for outgoing_message in self.outgoing_messages:
			self.transport.write(outgoing_message.message())
			self.peer.update_last_contact()

		# print (self.peer.status())


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
