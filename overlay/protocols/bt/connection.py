from twisted.internet.protocol import Protocol
import struct
from overlay.log import logger_bt as log
from overlay.utils import short_hash


# Schedule requests on UNCHOKE and REJECT and CHUNK


HELLO = 0x80 + 0
CHOKE = 0x80 + 1
UNCHOKE = 0x80 + 2
INTERESTED = 0x80 + 3
NOT_INTERESTED = 0x80 + 4
HAVE = 0x80 + 5
HAVE_NONE = 0x80 + 6
HAVE_ALL = 0x80 + 7
HAVE_SOME = 0x80 + 8
REQUEST = 0x80 + 9
REJECT = 0x80 + 10
CANCEL = 0x80 + 11
CHUNK = 0x80 + 12


command_names = {
    HELLO : "HELLO",
    CHOKE : "CHOKE",
    UNCHOKE : "UNCHOKE",
    INTERESTED : "INTERESTED",
    NOT_INTERESTED : "NOT_INTERESTED",
    HAVE : "HAVE",
    HAVE_NONE : "HAVE_NONE",
    HAVE_ALL : "HAVE_ALL",
    HAVE_SOME : "HAVE_SOME",
    REQUEST : "REQUEST",
    REJECT : "REJECT",
    CANCEL : "CANCEL",
    CHUNK : "CHUNK"
    }


def split(sequence, n):
    l = list(sequence)
    while sequence:
        yield sequence[:n]
        sequence = sequence[n:]


class Connection(Protocol):
    """

    @ivar _pending: C{list} of outstanding chunk requests.
    """

    def __init__(self, controller, metainfo):
        self.controller = controller
        self.metainfo = metainfo
        self._pending = list()
        self._connected = False
        self._pieces = set()
        self._choked = True 		# remote state
        self._interested = False
        self._choking = True		# local state
        self._interesting = False

    def pieces(self):
        return iter(self._pieces)

    def have(self, index):
        return index in self._pieces

    def rate(self):
        return 0

    def pending(self):
        """
        Return list of pending requests.

        @return: sequence of pending requests
        """
        return self._pending

    def connectionLost(self, reason):
        """
        Connection has been lost to the remote peer.
        """
        log.info("connection lost")
        print "CONNECTION LOST FOR SOME REASON"
        if self._connected:
            self.controller.connectionLost(self)
            self.controller.requestsRejected(self, self.pending())

    def connectionMade(self):
        """
        Connection has been made, start negotiation.
        """
        log.info("connection made")
        self.transport.sendMessage(HELLO, '')

    def gotHELLO(self, capabilities):
        self.controller.connectionMade(self)
        self.negotiate()

    def sendHave(self, *pieces):
        """
        Send HAVE to remote peer to inform it that we now can provide
        the specified pieces.
        """
        hashes = list()
        for piece in pieces:
            hashes.append(self.metainfo.getHash(piece))
        self.transport.sendMessage(HAVE, ''.join(hashes))

    def gotHAVE(self, data):
        """
        """
        pieces = list()
        while data:
            try:
                pieces.append(self.metainfo.getIndex(data[:20]))
            except IndexError:
                self.transport.loseConnection()
                raise
            data = data[20:]
        self._pieces.update(pieces)
        self.controller.gotHave(self, pieces)

    def choking(self):
        """
        """
        return self._choking

    def sendChoke(self):
        """
        """
        if not self._choking:
            self._choking = True
            self.transport.sendMessage(CHOKE, '')

    def sendUnchoke(self):
        """
        """
        if self._choking:
            self._choking = False
            self.transport.sendMessage(UNCHOKE, '')

    def interesting(self):
        return self._interesting

    def sendInteresting(self):
        """
        """
        if not self._interesting:
            self._interesting = True
            self.transport.sendMessage(INTERESTED, '')

    def sendNotInteresting(self):
        if self._interesting:
            self._interesting = False
            self.transport.sendMessage(NOT_INTERESTED, '')

    def negotiate(self):
        n = self.controller.storage.getNumberCompleted()
        if n == self.metainfo.numPieces:
            self.transport.sendMessage(HAVE_ALL, '')
        elif n == 0:
            self.transport.sendMessage(HAVE_NONE, '')
        elif n*20 < (self.metainfo.numPieces / 8):
            self.sendHave(*self.controller.storage.completed())
        else:
            self.sendHave(*self.controller.storage.completed())
            print "IMPLEMENT HAVE SOME"
        self._connected = True

    def messageReceived(self, opcode, data):
        """
        """
        log.debug("message received: %s (with %d bytes of data)",
                  command_names.get(opcode, hex(opcode)), len(data))
        if not self._connected:
            if opcode != HELLO:
                self.transport.loseConnection()
            return self.gotHELLO(split(data, 16))
        try:
            if opcode == CHOKE:
                self.gotCHOKE()
            elif opcode == UNCHOKE:
                self.gotUNCHOKE()
            elif opcode == INTERESTED:
                self.gotINTERESTED()
            elif opcode == NOT_INTERESTED:
                self.gotNOTINTERESTED()
            elif opcode == HAVE:
                self.gotHAVE(data)
            elif opcode == HAVE_ALL:
                numPieces = self.metainfo.numPieces
                self._pieces.update(range(numPieces))
                self.controller.gotHave(self, range(numPieces))
            elif opcode == HAVE_NONE:
                self.controller.gotHave(self, [])
            elif opcode == HAVE_SOME:
                assert False
            elif opcode == REQUEST:
                hash, offset, length = struct.unpack("!20sII", data)
                self.gotREQUEST(hash, offset, length)
            elif opcode == REJECT:
                hash, offset, length = struct.unpack("!20sII", data)
                self.gotREJECT(hash, offset, length)
            elif opcode == CHUNK:
                hash, offset = struct.unpack("!20sI", data[:24])
                self.gotCHUNK(hash, offset, data[24:])
            elif opcode == CANCEL:
                hash, offset, length = struct.unpack("!20sII", data)
                self.gotCANCEL(hash, offset, length)
            else:
                self.transport.loseConnection()
        except struct.error:
            self.transport.loseConnection()
            raise

    def interested(self):
        """
        """
        return self._interested

    def gotINTERESTED(self):
        """
        """
        if not self._interested:
            self._interested = True
            self.controller.choker.interested(self)

    def gotNOTINTERESTED(self):
        """
        """
        if self._interested:
            self._interested = False
            self.controller.choker.notInterested(self)

    def choked(self):
        """
        """
        return self._choked

    def gotUNCHOKE(self):
        """
        Process incoming UNCHOKE message from remote peer.
        """
        if self._choked:
            self._choked = False
            self.controller.requestMore(self)

    def gotCHOKE(self):
        """
        Process incoming CHOKE message from remote peer.
        """
        if not self._choked:
            self._choked = True

    def gotREJECT(self, index, offset, length):
        """
        Process incoming REJECT meesage from remote peer.

        @param index: piece index
        @param begin: chunk offset
        @param length: length of chunk
        """
        try:
            self._pending.remove((index, offset, length))
        except ValueError:
            return
        self.scheduler.requestRejected(index, offset, length)

    def sendChunk(self, hash, offset, data):
        """
        Send a chunk of data to the remote peer.
        """
        log.debug("sending cbunk with hash %s @ %s (%d bytes)",
                  short_hash(hash), hex(offset), len(data))
        self.transport.sendMessage(
            CHUNK, struct.pack("!20sI", hash, offset) + data
            )

    def gotCHUNK(self, hash, offset, data):
        """
        Received a chunk of data from the remote peer.
        """
        log.debug("received chunk with hash %s @ %s (%d bytes)",
                  short_hash(hash), hex(offset), len(data))
        try:
            piece = self.metainfo.getIndex(hash)
            self._pending.remove((piece, offset, len(data)))
        except (ValueError, IndexError), e:
            raise
        self.controller.requestHonored(self, piece, offset, data)

    def gotREQUEST(self, hash, offset, length):
        """
        """
        log.debug("received request for hash %s @ %s (%d bytes)",
                  short_hash(hash), hex(offset), length)
        try:
            piece = self.metainfo.getIndex(hash)
        except IndexError:
            raise
        data = self.controller.storage.read(piece, offset, length)
        self.sendChunk(hash, offset, data)

    def request(self, piece, offset, length):
        """
        Request a chunk.

        @param piece: piece index
        """
        self._pending.append((piece, offset, length))
        h = self.metainfo.getHash(piece)
        self.transport.sendMessage(
            REQUEST, struct.pack("!20sII", h, offset, length)
            )
                                              
                            
