# Originally written by Bram Cohen.
# Adopted to Twisted by Johan Rydberg.

from overlay.protocols.bt.utils import TickCall
from random import randrange


class Choker:
    """
    The choker is resposible for determining which of the connected
    peers should be allowed to fetch pieces from us.

    The state of the connections are re-evaluated once every 10th
    second.  Every 30th second a new connection is given the chance to
    fetch pieces.  

    @ivar maxUploads: The maximum number of concurrent uploads.
    """

    def __init__(self, maxUploads=4, clock=None):
        self.tick = TickCall(10, clock)
        self.tick.add(3, self.optimisticUnchoke)
        self.tick.add(1, self.rechoke)
        self.maxUploads = maxUploads
        self.connections = list()

    def connectionMade(self, connection, p=None):
        """
        Add a L{IConnection} that should be target for this choker.

        Will cause the choker to reevaluate all connections.
        """
        if p is None:
            p = randrange(-2, len(self.connections) + 1)
        self.connections.insert(max(p, 0), connection)
        connection.choker = self
        self.rechoke()

    def connectionLost(self, connection):
        """
        Remove a L{IConnection} from the choker.

        Might cause the choker to reevaluate all connections.
        """
        self.connections.remove(connection)
        if connection.interested() and not connection.choking():
            self.rechoke()
        connection.choker = None

    def interested(self, connection):
        """
        Inform the choker that the given L{IConnection} is interesting
        in one or many of our pieces.

        May cause the choker to reevaluate all connections.
        """
        if not connection.choking():
            self.rechoke()

    def notInterested(self, connection):
        """
        Inform the choker that the given L{IConnection} is no long
        interesting in any of our pieces.

        May cause the choker to reevaluate all connections.
        """
        if not connection.choking():
            self.rechoke()

    def optimisticUnchoke(self):
        """
        Iterate through connections and reorder the connections so
        that a new connection might get the change to talk to us.
        """
        for i in range(len(self.connections)):
            connection = self.connections[i]
            if connection.choking() and connection.interested():
                self.connections = self.connections[i:] + self.connections[:i]
                break

    def _getPreferred(self):
        """
        Return a list of preferred connections, determined by some
        implementation detail.
        """
        preferred = list()
        for connection in self.connections:
            # if snubbed
            if True and connection.interested():
                preferred.append((-connection.rate(), connection))
        preferred.sort()
        del preferred[self.maxUploads - 1:] 
        return [x[1] for x in preferred]

    def rechoke(self):
        """
        Reevaluate connection states.
        """
        preferred = self._getPreferred()
        #print "preferred", preferred
        count = len(preferred)
        for connection in self.connections:
            if connection in preferred:
                connection.sendUnchoke()
            else:
                if count < self.maxUploads:
                    connection.sendUnchoke()
                    if connection.interested():
                        count += 1
                else:
                    connection.sendChoke()

    def setMaxUploads(self, maxUploads):
        """
        Set maximum number of concurrent uploads.

        Will cause the choker to reevaluate all connections.
        """
        self.maxUploads = maxUploads
        self.rechoke()
        
