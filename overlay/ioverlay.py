# Written by Johan Rydberg <johan.rydberg@gmail.com>

from zope.interface import Interface, Attribute
from twisted.internet.interfaces import IProtocol


class IOverlayTransport(Interface):
    """
    Message based path transport that runs on top of the overlay.
    """

    def sendMessage(opcode, data):
        """
        Send an application message along the path.

        @param opcode: message opcode
        ©type  opcode: L{int} between 0x80 and 0xff
        @param data: message payload
        @type  data: L{str}
        """


class IOverlayProtocol(IProtocol):
    """
    Message based protocol interface that runs on top of a
    IOverlayTransport.
    """
    
    def messageReceived(opcode, data):
        """
        Message received with the given opcode and payload.
        """

        
class IConnection(Interface):
    """Connection to a friend, either established by this node or the
    friend.
    """

    connection_id = Attribute("unique id of the connection")

    def route(path, data, source):
        """Route data originating from source to the given path on the
        connection.

        C{source} is the IConnection from with the data originated.
        Used for fair packet scheduling.
        """

    def notifyOnDisconnect(callback):
        """Tell the connection that callback wants to be notified when
        the connection dies.
        """

    def getRate():
        """Return rate of data from connection.
        """

    def updateRate(count):
        """Update the rate.
        """

    def sendSEARCH(ttl, q, sid, source=None):
        """Transmit a SEARCH on the connection.

        @param source: Connection from with the operation originaly
            originated.  If None, do not do packet scheduling.
        """

    def sendCONNECT(sid, pid, source=None):
        """Transmit a CONNECT on the connection.

        @param source: Connection from with the operation originaly
            originated.  If None, do not do packet scheduling.
        """

    def sendROUTE(pid, data, source=None):
        """Transmit a ROUTE on the connection.

        @param source: Connection from with the operation originaly
            originated.  If None, do not do packet scheduling.
        """

    def sendHANGUP(pid, data, source=None):
        """Transmit a HANGUP on the connection.

        @param source: Connection from with the operation originaly
            originated.  If None, do not do packet scheduling.
        """

    def sendSTATE(new_state):
        """Transmit a STATE on the connection.
        """


class IOverlayRouter(Interface):

    def receivedSEARCH(connection, ttl, q, sid):
        """SEARCH received from the given connection.
        """

    def receivedCONNECT(connection, sid, pid):
        """CONNECT received from the given connection for the
        specified search id.

        PID is the path identifier on the given connection.
        """

    def receivedROUTE(connection, pid, data):
        """ROUTE received from the given connection for the
        specified path id.
        """

    def receivedHANGUP(connection, pid):
        """HANGUP received from the given connection for the
        specified path id.
        """
        
    def receivedSTATE(connection, new_state):
        """Received new state from the connection.
        """
