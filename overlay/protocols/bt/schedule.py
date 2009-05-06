# Copyright (C) 2009 Johan Rydberg <johan.rydberg@gmail.com>
# See LICENSE.txt for information on what you may and may not do with
# this code.


class Schedule:

    def __init__(self, storage, metainfo, chunksize):
        self.storage = storage
        self.pending = [None] * metainfo.numPieces
        self.metainfo = metainfo
        ps = metainfo.pieceSize
        ts = metainfo.totalSize
        self._done = True
        for pi in range(metainfo.numPieces):
            low = pi * ps
            high = low + ps
            if high > ts:
                high = ts
            self.pending[pi] = list()
            if not storage.have(pi):
                for plow in range(low, high, chunksize):
                    phigh = plow + chunksize
                    if phigh > high:
                        phigh = high
                    self.pending[pi].append(((plow - low), (phigh - plow)))
                self._done = False
        self.active = [None] * len(self.pending)
        
    def done(self):
        """
        """
        if not self._done: 
            for i in range(self.metainfo.numPieces):
                if self.pending[i] or self.active[i]:
                    return False
            self._done = True
        return self._done
        
    def haveRequests(self, piece):
        """
        Return C{True} if the schedule have any requests for the given
        piece.
        """
        # FIXME: should this include active?
        return len(self.pending[piece]) != 0

    def getRequest(self, piece):
        """
        Return a chunk request for the specified piece or None if
        there are no more pending requests for the piece.

        @param piece: piece index
        """
        try:
            offset, length = self.pending[piece].pop(0)
        except IndexError:
            return None
        if self.active[piece] is None:
            self.active[piece] = list()
        self.active[piece].append((offset, length))
        return offset, length

    def honorRequest(self, piece, offset, length):
        """
        Inform the scheduler that a request has been honored and is no
        longer considered active.
        """
        try:
            self.active[piece].remove((offset, length))
        except ValueError:
            raise

    def putRequest(self, piece, offset, length):
        """
        Return a request to the scheduler that has been rejected or
        lost.
        """
        try:
            self.active[piece].remove((offset, length))
        except ValueError:
            raise
        p = len(self.pending[piece]) != 0
        self.pending[piece].append((offset, length))
        return p
