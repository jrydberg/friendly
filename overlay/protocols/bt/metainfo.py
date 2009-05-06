# Copyright (C) 2009 Johan Rydberg <johan.rydberg@gmail.com>
# See LICENSE.txt for information on what you may and may not do with
# this code.


class AbstractMetaInfo(object):
    """
    Abstract base class for implementors of L{IMetaInfo}

    @ivar hashes: list of all SHA-1 hashes
    """

    def __init__(self):
        self.hashes = list()
        self.totalSize = 0
        
    def getHash(self, piece):
        """
        Return 20-byte string that is the hash of the specified piece.

        @param piece: index of piece to get the hash of
        """
        return self.hashes[piece]
        
    def getIndex(self, hash):
        """
        Return index of the piece thas has the given hash.  Raises
        L{IndexError} if there is no piece with that hash.

        @return: piece index
        @rtype: C{int}
        """
        return self.hashes.index(hash)
