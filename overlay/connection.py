from twisted.internet import protocol, interfaces, ssl
from zope.interface import implements
from overlay.ssl import ISSLProtocol
from overlay.utils import randbytes
import bisect, struct


PROBE = 0
ESTABLISH = 1
RESET = 2


class SCFQ:
    """Self Clocked Fair Queueing.
    """

    def __init__(self, weighter=lambda x: 1.0):
        self.queue = list()
        self.currentFinish = 0
        self.flows = dict()
        self.weighter = weighter

    def _calcFinishTime(self, data, nextTime, flow):
        """
        Calculate finish time for packet originating from L{flow}.
        """
        weight = self.weighter(flow)
        try:
            ratio = float(len(data)) / weight
        except ZeroDivisionError:
            return 0
        if nextTime > self.currentFinish:
            return nextTime + int(ratio)
        else:
            return self.currentFinish + int(ratio)

    def enqueue(self, data, flow):
        """
        Put data packet into the queue identified by L{sourceFlow}

        @type sourceFlow: a hashable that identifies the flow
        """
        nextTime = self.flows.get(flow, self.currentFinish)
        paketTime = self._calcFinishTime(data, nextTime, flow)
        self.flows[flow] = paketTime
        bisect.insort_right(self.queue, (paketTime, data))

    def __len__(self):
        """
        Return length of the queue.
        """
        return len(self.queue)

    def dequeue(self):
        """
        Dequeue a packet from the queue and return it.

        @return: L{None} if there the queue is empty.
        """
        if not len(self.queue):
            return None
        self.currentFinish, data = self.queue.pop(0)
        return data




class Connection(protocol.Protocol):
    implements(interfaces.IPushProducer, ISSLProtocol)

    # Remaing to do is to decide if the connection should have a
    # "expected" certificate, so that the verifier can warn.

    def __init__(self, controller, verifier):
        self.controller = controller
        self.verifier = verifier
        self.friend = None
        self.connection_id = randbytes(20)
        self.paused = False
        self.queue = SCFQ()
        self.recvd = ''

    def getFriend(self):
        """
        Return the friend that this connection is associated with.

        @rtype: L{IFriend}
        """
        return self.friend

    def _cbConnect(self, friend):
        self.friend = friend
        try:
            #print self.controller.connections
            self.controller.connectionMade(self)
        except ValueError:
            self.friend = None
            #print id(self), "could not make a real connection"
            self.transport.loseConnection()
        else:
            #print "real connection made"
            self.transport.registerProducer(self, True)

    def _ebConnect(self, reason):
        reason.printTraceback()
        self.transport.loseConnection()

    def connectionLost(self, reason):
        if self.friend is not None:
            #print id(self), "real connection lost"
            self.controller.connectionLost(self)
            self.transport.unregisterProducer()
        #else:
        #    print "non-real connection lost"

    def handshakeDone(self):
        self.transport.logstr = self.controller.i
        cert = ssl.Certificate.peerFromTransport(self.transport)
        #print "CONNECTON ESTABLISHED TO", cert.digest()
        #print "  MY NAME IS", self.controller.i
        d = self.verifier.verifyFriend(cert)
        d.addCallback(self._cbConnect).addErrback(self._ebConnect)

    def loseConnection(self):
        """
        Lose connection.
        """
        #print "lose connection"
        self.transport.loseConnection()

    def _produce(self):
        """
        Produce data to the transport while not paused.
        """
        while not self.paused and len(self.queue) != 0:
            self.transport.write(self.queue.dequeue())

    # Outbound:
    def sendMessage(self, opcode, data, flow):
        l = len(data)
        hdr = struct.pack("!BBH", opcode, l >> 16, l & 0xffff)
        self.queue.enqueue(hdr + data, flow)
        self._produce()

    def sendPROBE(self, q, cid, sid, ttl, flow):
        """
        Transmit probe request.
        """
        self.sendMessage(
            PROBE, struct.pack("20s20s20sxxxB", q, cid, sid, ttl), flow
            )

    def sendESTABLISH(self, pid, cid, sid, flow):
        self.sendMessage(ESTABLISH, struct.pack("20s20s20s", pid, cid, sid),
                         flow)

    def sendAppMessage(self, pid, cid, opcode, data, flow):
        self.sendMessage(
            opcode, struct.pack("20s20s", pid, cid) + data, flow
            )
        
    # Inbound:
    def dataReceived(self, recvd):
        """
        Convert header prefixed messages into calls to messageRecevied.
        """
        #print "data received"
        self.recvd = self.recvd + recvd
        while len(self.recvd) > 3:
            opcode, lenhi, lenlo = struct.unpack("!BBH", self.recvd[:4])
            l = (lenhi << 16) + lenlo
            if len(self.recvd) < l + 4:
                break
            packet = self.recvd[4:l+4]
            self.recvd = self.recvd[l+4:]
            self.messageReceived(opcode, packet)

    def messageReceived(self, opcode, data):
        try:
            if opcode == PROBE:
                q, cid, sid, ttl = struct.unpack("20s20s20sxxxB", data)
                self.controller.receivedPROBE(q, cid, sid, ttl, self)
            elif opcode == ESTABLISH:
                pid, cid, sid = struct.unpack("20s20s20s", data)
                self.controller.receivedESTABLISH(pid, cid, sid, self)
            elif opcode == RESET:
                pid, cid = struct.unpack("20s20s", data)
                self.controller.receivedRESET(pid, cid, self)
            elif opcode >= 0x80:	# application message
                pid, cid = struct.unpack("20s20s", data[:40])
                self.controller.receivedAppMessage(
                    pid, cid, opcode, data[40:], self
                    )
        except struct.error:
            raise

    # IPushProducer:
    def pauseProducing(self):
        """
        Pause producing data.
        """
        self.paused = True

    def stopProducing(self):
        """
        Stop producing data.
        """
        self.paused = True

    def resumeProducing(self):
        """
        Resume producing data.
        """
        print "resume producing"
        self.paused = False
        self._produce()

    def __repr__(self):
        if self.friend:
            return "<Connection to %s>" % self.friend.getIdentity()
        else:
            return "<Connection to -unknown->"

