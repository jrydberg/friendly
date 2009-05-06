
#
#
#


class Controller:

    def __init__(self, choker, schedule, storage, picker, backlog=5):
        self.choker = choker
        self.schedule = schedule
        self.storage = storage
        self.connections = list()
        self.picker = picker
        self._backlog = backlog
        self.delegate = None

    def setDelegate(self, delegate):
        """
        Set delegate.
        """
        self.delegate = delegate

    def getDelegate(self):
        """
        Return current delegate.
        """
        return self.delegate
        
    def setBacklog(self, backlog):
        """
        Set the number of pending requests that a connection may have
        at any time.
        """
        self._backlog = backlog

    def backlog(self):
        """
        Return the number of pending requests that a connection may
        have at any time.
        """
        return self._backlog

    def connectionLost(self, connection):
        """
        The given connection has just been lost.

        @param connection: L{IConnection}
        """
        self.connections.remove(connection)
        for piece in connection.pieces():
            self.picker.lostHave(piece)
        self.choker.connectionLost(connection)
        if self.delegate is not None:
            self.delegate.connectionLost(connection)
        
    def connectionMade(self, connection):
        """
        The given connection has just been made.  The connection has
        been authenticated.

        @param connection: L{IConnection}
        """
        self.connections.append(connection)
        self.choker.connectionMade(connection)
        if self.delegate is not None:
            self.delegate.connectionMade(connection)

    def gotHave(self, connection, pieces):
        """
        Inform controller that the peer represented by connection has
        the pieces specified in C{pieces}.

        Prior to calling this the connection should establish state so
        that C{connection.have(piece)} for any of the pieces in
        C{pieces} returns C{True}.
        """
        for piece in pieces:
            self.picker.gotHave(piece)
        self.checkInterest(connection, pieces)
        self.requestMore(connection, pieces)

    def requestMore(self, connection, pieces=None):
        """
        Try to request more chunks through the given connection.
        """
        if connection.choked() or len(connection.pending()) == self.backlog():
            return
        
        if pieces is None:
            pieces = self.picker

        completed = list()
        for piece in pieces:
            if not connection.have(piece):
                continue
            while len(connection.pending()) != self.backlog():
                try:
                    offset, length = self.schedule.getRequest(piece)
                except TypeError:
                    break
                connection.request(piece, offset, length)
            else:
                return	# backlog reached
            completed.append(piece)
        if completed:
            for connection in self.connections:
                self.checkLostInterest(connection, completed)

    def requestRejected(self, connection, piece, offset, length):
        """
        Inform controller that requested piece (specified by (piece,
        offset, length)) was rejected by the remote peer represented
        by C{connection}.

        @param connection: L{IConnection}
        """
        self.requestsRejected(connection, [(piece, offset, length)])

    def requestsRejected(self, connection, requests):
        """
        Inform controller that a set of requests has been rejected or
        lost.
        """
        pieces = list()
        for piece, offset, length in requests:
            # putRequest returns True if there was any previous
            # requests pending for the piece.
            if not self.schedule.putRequest(piece, offset, length):
                pieces.append(piece)
        if pieces:
            for connection in self.connections:
                self.checkInterest(connection, pieces)
                self.requestMore(connection, pieces)

    def requestHonored(self, connection, piece, offset, data):
        """
        Inform controller that the request for piece (specified by
        (piece, offset, data)) was honored.
        """
        self.picker.chunkReceived(piece)
        self.schedule.honorRequest(piece, offset, len(data))
        completed = self.storage.write(piece, offset, data)
        if completed:
            self.picker.complete(piece)
            for t in self.connections:
                t.sendHave(piece)
        self.requestMore(connection)
        if not len(connection.pending()):
            connection.sendNotInteresting()
                
    def checkInterest(self, connection, pieces):
        """
        Check if we are interested in any of the specified pieces.
        """
        if connection.interesting():
            return
        for piece in pieces:
            if connection.have(piece) and self.schedule.haveRequests(piece):
                connection.sendInteresting()
                break

    def checkLostInterest(self, connection, pieces):
        """
        Check if we have lost interest in the given connection, based
        on that there are no more requests availble for the given
        pieces.
        
        @type pieces: C{list} of pieces that have no more pending
            requests
        """
        if not connection.interesting() or len(connection.pending()):
            # the peer is considered interesting if we have pending
            # requests
            return
        #for piece in pieces:
        #    if connection.have(piece):
        #        break
        #else:
        #    return
        for piece in connection.pieces():
            if self.schedule.haveRequests(piece):
                return
        connection.sendNotInteresting()
