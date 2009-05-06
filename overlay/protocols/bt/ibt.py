from zope.interface import Interface, Attribute


class IMetaInfo(Interface):
    """
    Implementors of this interface provides information about how to
    share data.
    """
    rootHash = Attribute(
        """hash that identifies the data that this IMetaInfo represents"""
        )
    pieceSize = Attribute("size in bytes of a piece")
    totalSize = Attribute("total number of bytes")
    numPieces = Attribute("total number of pieces")

    def getHash(piece):
        """
        Return 20-byte string that is the hash of the specified piece.

        @param piece: index of piece to get the hash of
        """

    def getIndex(hash):
        """
        Return index of the piece thas has the given hash.  Raises
        L{IndexError} if there is no piece with that hash.

        @return: piece index
        @rtype: C{int}
        """


class IStorage(Interface):

    def getNumberCompleted():
        """
        Return the number of completed pieces in the storage.

        @rtype: C{int}
        """

    def iterCompleted():
        """
        Returns a iterator that will iterate through all currently
        completed pieces.
        """

    def have(piece):
        """
        Return C{True} if the storage has a completed version of the
        specified piece.
        """

    def check(progress):
        """
        Check for preexisting content in the storage. This should be
        done before attached to any controller.

        If the storage already has been checked this can be treated as
        a nop.
        
        C{progress} is an optional one argument function that will be
        called with progress information throughout the check.

        @return: A deferred that is called when the checking is done.
        """

    def read(piece, offset, length):
        """
        Read content for a chunk of a piece.
        
        @param piece: index of piece
        @param offset: offset of chunk
        @param length: length of chunk
        """

    def write(piece, offset, data):
        """
        Write chunk content of the storage.

        @param piece: index of piece
        @param offset: offset in piece
        @param data: the data to write
        @return: C{True} if this write completes piece.
        """

