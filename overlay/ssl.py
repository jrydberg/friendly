from twisted.internet import (reactor, ssl, tcp, interfaces, main,
                              protocol, defer)
from zope.interface import Interface, implements
from twisted.python import log
import OpenSSL


"""
This module contains some additional functionality to the SSL support
in Twisted.

Currently Twisted does not notify a protocol implementation when the
SSL handshake is finished.

A new protocol interface is introduced: L{ISSLProtocol}.  If the
protocol provides this interface, the L{handshakeDone} method will be
invoked as soon as the handshake is finished.
"""


class ISSLProtocol(interfaces.IProtocol):
    """
    Protocol that notifies the user when SSL handshake is finished.
    """

    def handshakeDone():
        """
        Handshake is done.  From this point on the return value of
        L{getPeerCertificate} is known to be valid.
        """


class HandshakeMixin:

    def doHandshake(self):
        try:
            err = self.socket.do_handshake()
        except OpenSSL.SSL.WantReadError:
            self.startReading()
            self.stopWriting()
        except OpenSSL.SSL.WantWriteError:
            self.startWriting()
        except OpenSSL.SSL.ZeroReturnError:
            return main.CONNECTION_LOST
        except OpenSSL.SSL.SysCallError, e:
            if e[0] == -1: # data == ""
                # errors when writing empty strings are expected
                # and can be ignored
                return 0
            else:
                return main.CONNECTION_LOST
        except OpenSSL.SSL.Error, e:
            return e
        else:
            del self.doRead
            del self.doWrite
            self.stopWriting()
            self.stopReading()
            self._handshakeDone()

    def _handshakeDone(self):
        try:
            self.protocol.handshakeDone()
        except Exception, e:
            log.deferr()
            self.socket.close()
        else:
            self.startReading()


class Server(ssl.Server, HandshakeMixin):
    pass


class Port(ssl.Port):
    transport = Server

    def _preMakeConnection(self, transport):
        # *Don't* call startTLS here
        # The transport already has the SSL.Connection object from above
        transport._startTLS()
        if ISSLProtocol.providedBy(transport.protocol):
            transport.doRead = transport.doWrite = transport.doHandshake
        return tcp.Port._preMakeConnection(self, transport)


class Client(ssl.Client, HandshakeMixin):

    def _connectDone(self):
        ssl.Client._connectDone(self)
        if ISSLProtocol.providedBy(self.protocol):
            self.doRead = self.doWrite = self.doHandshake


class Connector(ssl.Connector):

    def _makeTransport(self):
        return Client(self.host, self.port, self.bindAddress,
                      self.contextFactory, self, self.reactor)


class ClientCreator(protocol.ClientCreator):
    """
    ClientCreator that can be used with a L{IConnector}.

    See L{twisted.internet.protocol.ClientCreator}
    """

    def getFactory(self):
        d = defer.Deferred()
        return protocol._InstanceFactory(
            self.reactor, self.protocolClass(*self.args, **self.kwargs), d
            )

    def connectWith(self, connectorType, *args, **kw):
        return self.reactor.connectWith(connectorType, *args, **kw)


# UGLY TEST CODE:


# class ProtocolX(Protocol):
#     implements(ISSLProtocol)

#     def handshakeDone(self):
#         print "HANDSHAKE DONE"
#         print self.transport.getPeerCertificate()

#     def connectionMade(self, *args):
#         print "GOT CONNECTION"
#         print self.transport.getPeerCertificate()
#         print "self transport", self.transport

#     def dataReceived(self, data):
#         print "got data", data
#         print "cert is ", self.transport.getPeerCertificate()
#         print self.transport
#         self.transport.write(data)

#     def connectionLost(self, reason):
#         print "connection lost"

# from twisted.internet.protocol import ClientFactory, Protocol


# from twisted.python import log
# import sys

# log.startLogging(sys.stdout)

# factory = ClientFactory()
# factory.protocol = ProtocolX

# #connector = Connector('www.google.se', 443, factory,
# #                      ssl.ClientContextFactory(), 30, None,
# #                      reactor=reactor)
# #print reactor
# #connector.connect()

# ctxFactory = ssl.ClientContextFactory()
# ctxFactory.method = OpenSSL.SSL.TLSv1_METHOD

# ctxFactory = ssl.DefaultOpenSSLContextFactory('p.pem', 'p.pem')

# port = Port(11111, factory, ctxFactory, reactor=reactor)
# port.startListening()

# reactor.run()


                    
