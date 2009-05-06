# Copyright (C) 2009 Johan Rydberg <johan.rydberg@gmail.com>
# See LICENSE.txt for information on what you may and may not do with
# this code.

from overlay.protocols.bt.ibt import IMetaInfo
from overlay.protocols.bt.bencode import bdecode, bendcode
from zope.interface import implements
from overlay.protocols.bt.metainfo import AbstractMetaInfo


class Torrent(AbstractMetaInfo):
    """
    L{IMetaInfo} provider based in the information from a I{.torrent}
    file.

    @ivar filelist: sequence of (filename, length) tuples.
    """
    implements(IMetaInfo)

    def __init__(self, file):
        """
        Create a new L{IMetaInfo} from a torrent file.

        Raises C{ValueError} if it is a bad torrent file.
        
        @param file: either a file-like object (something that has a
            I{read} method) or a filename.
        """
        AbstractMetaInfo.__init__(self)
        if not hasattr(file, "read"):
            file = open(file, 'rb')
        infodict = bdecode(file.read())['info']

        self.filelist = list()
        # single-file torrent if the info dictionary contains a
        # 'length' key:
        if infodict.has_key('length'):
            filename = infodict['name']
            self.filelist.append(
                (filename, infodict['length']),
                )
            self.totalSize = infodict['length']
        else:
            dirname = infodict['name']
            for filedict in infodict['files']:
                filename = os.path.join(dirname, *filedict['path'])
                self.filelist.append(
                    (filename, filedict['length'])
                    )
                self.totalSize += filedict['length']
        
        # iterate through and construct the list of hashes
        data = infodict['pieces']
        while data:
            self.hashes.append(data[:20])
            data = data[20:]

        # calculate the info hash for the torrent:
        self.rootHash = sha(bencode(infodict)).digest()
        self.numPieces = len(self.hashes)
        self.pieceSize = infodict['piece length']
