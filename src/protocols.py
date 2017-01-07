from constants import PROTOCOL_STRING
from helpermethods import convert_int_to_hex
from twisted.internet.protocol import Protocol, ClientFactory

"""
This file defines the coast TCP implementation of the BitTorrent protocol in interacting with
peers
"""


class PeerProtocol(Protocol):
    def __init__(self, factory, ip, port):
        self.factory = factory
        self.ip = ip
        self.port = port

    def connectionMade(self):
        print ("Connection made to peer ({}:{})".format(self.factory.ip, self.factory.port))
        print ("Sending handshake: {}".format(self.factory.torrent.get_handshake()))

        self.transport.write(self.factory.torrent.get_handshake())

    def dataReceived(self, data):
        print ("Data received from peer ({}:{}): {}".format(self.ip, self.port, data))


class PeerFactory(ClientFactory):
    def __init__(self, torrent, ip, port):
        self.torrent = torrent
        self.protocols = []
        self.ip = ip
        self.port = port

    def startedConnecting(self, connector):
        print ("Starting connection to peer ({}: {})".format(self.ip, self.port))

    def buildProtocol(self, addr):
        protocol = PeerProtocol(self, self.ip, self.port)
        self.protocols.append(protocol)
        return protocol

    def clientConnectionLost(self, connector, reason):
        print ("Lost connection to peer ({}:{}): {}".format(self.ip, self.port, reason))

    def clientConnectionFailed(self, connector, reason):
        print ("Connection failed to peer ({}:{}): {}".format(self.ip, self.port, reason))
