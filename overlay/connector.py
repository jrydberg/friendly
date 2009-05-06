from twisted.internet import reactor
from overlay.log import logger_connector as log
from random import randrange
import random


class Connector:
    """
    The connector is responsible for determening which fellow peers we
    should be and stay connected to.  It operates on endpoints.

    @ivar connectionFactory:
    @type connectionFactory: L{callable} that is fed a L{IFriend} and
        returns a deferred that will be called when connection is
        made
    """

    def __init__(self, connectionFactory):
        self.connectionFactory = connectionFactory
        self.friends = list()
        self.connections = dict()	# friend -> connection
        self.pending = dict()		# friend -> deferred
        self.callID = None

    def addFriend(self, friend):
        """
        Add a friend to the connector for connection considerations.
        
        The friend must have valid endpoint information.
        """
        if friend in self.friends:
            raise ValueError("friend already in connector")
        if not self.friends:
            self.friends.append(friend)
        else:
            p = randrange(0, len(self.friends))
            self.friends.insert(p, friend)
        if not friend in self.connections:
            self.schedule()

    def schedule(self):
        if self.callID is None:
            t = random.randint(0, 5)
            self.callID = reactor.callLater(t, self.reconnect)

    def removeFriend(self, friend):
        """
        Remove a friend from the connector.

        This will lose any connections with the friend.
        """
        if friend not in self.friends:
            raise ValueError("friend not in connector")
        self.friends.remove(friend)
        if not friend in self.connections:
            return
        self.connections[friend].loseConnection()
        # XXX: should we remove the friend here, or let it be
        # deleted is connectionLost?
        del self.connections[friend]	# XXX: do this?
        self.schedule()

    def connectionMade(self, connection):
        """
        Connection to has been made and the friend has been verified.

        @param connection: the new connection
        """
        if connection.getFriend() in self.connections:
            #print "KILL CONNECTON, duplicate"
            return connection.loseConnection()
        self.connections[connection.getFriend()] = connection
        #print "connector: add", connection.getFriend().getIdentity()
        self.schedule()

    def connectionLost(self, connection):
        """
        Connection has been lost.

        @param connection: the connection that was lost
        """
        if connection.getFriend() in self.connections:
            del self.connections[connection.getFriend()]
            # should we really try to connect directly on a lost
            # connection?
            self.schedule()

    def _connect(self, friend):
        """
        Connect to the specified friend.
        """
        def cb(protocol, friend):
            del self.pending[friend]
        def eb(failure, friend):
            log.info("failed to connect to %s", friend)
            del self.pending[friend]
        d = self.connectionFactory(friend)
        d.addCallback(cb, friend).addErrback(eb, friend)
        self.pending[friend] = d

    def inspect(self):
        print self.controller.i, "is connected to %d/%d" % (
            len(self.connections), len(self.friends))
        
    def reconnect(self):
        """
        Re-evaluate connection states for all known endpoints.
        """
        #print "reconnect"
        #print "  my connections", self.connections
        #print "  my friends", self.friends
        #print self.controller.i, "is connected to %d/%d" % (
        #    len(self.connections), len(self.friends))
        for friend in self.friends:
            if not friend in self.connections and \
                   not friend in self.pending:
                self._connect(friend)
        self.callID = None
        
        
