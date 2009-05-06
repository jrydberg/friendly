# Copyright (C) 2009 Johan Rydberg <johan.rydberg@gmail.com>
# See LICENSE.txt for information on what you may and may not do with
# this code.

from twisted.internet import task, defer
from zope.interface import implements

from overlay.protocols.bt.ibt import IStorage

from sha import sha
from stat import ST_SIZE
import os


def digest(data):
    return sha(data).digest()


class MultiFileStorage(object):
    """
    Provider of L{IStorage} that writes the content to multiple files.

    @ivar filelist: sequence of tuples of (filename, start, stop)
    @ivar readHandles: mapping between I{filename} and a C{file}
        object that is opened for reading.
    @ivar writeHandles: mapping between I{filename} and a C{file}
        object that is opened for writing.
    """
    implements(IStorage)
    
    def __init__(self, metainfo, filelist):
        """
        Create a new C{MultiFileStorage}.

        @param metainfo: something that provides L{IMetaInfo}
        @param filelist: sequence of (filename, length) tuples.
        """
        self.metainfo = metainfo
        self.filelist = list()
        start = 0
        # FIXME: make sure it is sorted
        for filename, length in filelist:
            self.filelist.append((filename, start, start + length))
            start = start + length
        self.readHandles = dict()
        self.writeHandles = dict()
        self.completed = set()

    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['readHandles']
        del odict['writeHandles']
        return odict

    def __setstate__(self, idict):
        self.__dict__ = idict
        self.readHandles = dict()
        self.writeHandles = dict()
        
    def check(self, progress=lambda x: None):
        """
        Check any preexisting content of the file and build an index
        of what pieces already exists.

        Returns a deferred that will be called when the checking is
        done.

        @param progress: a single argument function that will be
            called throughout the checking, with progress information
            in the interval [0, 1)
        """
        def _check():
            # badFiles contains filenames that could not be opened.
            # this will eliminate a open() syscall for each piece.
            badFiles = list()
            self.completed.clear()
            for n in range(self.metainfo.numPieces):
                for filename, offset, length \
                        in self.getIntervals(n, 0, self.metainfo.pieceSize):
                    if filename in badFiles:
                        continue
                    readHandle = self.getReadHandle(filename)
                    if readHandle is None:
                        badFiles.append(filename)
                    else:
                        readHandle.seek(offset)
                        if (digest(readHandle.read(length)
                                   == self.metainfo.getHash(n))):
                            self.completed.add(n)
                progress(n / float(self.metainfo.numPieces))
                yield None
        return task.coiterate(_check())

    def done(self):
        """
        Return C{True} if this storage has all content.
        """
        return len(self.completed) == self.metainfo.numPieces

    def getNumberCompleted(self):
        """
        Returns the number of completed pieces in the storage.
        """
        return len(self.completed)

    def iterCompleted(self):
        """
        Returns a iterator that will iterate through all currently
        completed pieces.
        """
        return iter(self.completed)

    def have(self, pieceIndex):
        """
        Return C{True} if the specified piece is in the storage.
        """
        return pieceIndex in self.completed

    def close(self):
        """
        Close all file handles.
        """
        handles = self.readHandles.values() + self.writeHandles.values()
        for handle in handles:
            handle.close()
        self.readHandles.clear()
        self.writeHandles.clear()

    def getIntervals(self, pieceIndex, offset, length):
        """
        Return a sequence of file intervals that span the given piece.

        @rtype: sequence of (filename, offset, length)
        """
        low = self.metainfo.piecesize * pieceIndex + offset	# FIXME: issue #6
        high = low + length
        for filename, start, stop in self.filelist:
            if start >= high or stop <= low:
                continue
            yield filename, low - start, min(stop, high) - low
            low = stop

    def getReadHandle(self, filename):
        """
        Return a read file handle for the given file. Also update the
        C{readHandles} mapping.
        """
        readHandle = self.readHandles.get(filename, None)
        if readHandles is not None:
            return readHandles
        
        try:
            readHandle = open(filename, 'r')
        except IOError:
            return None

        self.readHandles[filename] = readHandle
        return readHandle

    def read(self, pieceIndex, offset, length):
        """
        Read content for a chunk of a piece.
        
        @param offset: offset of chunk
        @param length: length of chunk
        """
        content = list()
        for filename, offset, length \
                in self.getIntervals(pieceIndex, offset, length):
            readHandle = self.getReadhandle(filename)
            if readHandle is None:
                raise IOError("no read handle")
            readHandle.seek(offset)
            content.append(readHandle.read(length))
        return ''.join(content)

    def getWriteHandle(self, filename):
        """
        Return a write file handle for the given file.  Also update
        the C{writeHandles} mapping.
        """
        writeHandle = self.writeHandles.get(filename, None)
        if writeHandle is not None:
            return writeHandle

        try:
            if os.path.exists(filename):
                writeHandle = open(filename, 'rb+')
            else:
                writeHandle = open(filename, 'w+')
        except IOError:
            dirname = os.path.dirname(filename)
            if dirname:
                try:
                    os.makedirs(dirname)
                except OSError:
                    pass
            writeHandle = open(filename, 'w+')

        # FIXME: should we allocate the file here?
        self.writeHandles[filename] = writeHandle
        return writeHandle

    def write(self, pieceIndex, offset, data):
        """
        Write chunk data to storage and return C{True} if this chunk
        completed the piece.

        @param piece: piece index
        @param offset: offset in piece
        @param data: chunk data
        """
        for filename, offset, length in \
                self.getIntervals(pieceIndex, offset, len(data)):
            writeHandle = self.getWriteHandle(filename)
            writeHandle.seek(offset)
            writeHandle.write(data[:length])
            data = data[length:]

        d = sha()
        for filename, offset, length in \
                self.getIntervals(pieceIndex, 0, self.metainfo.piecesize):
            readHandle = self.getReadHandle(filename)
            if readHandle is not None:
                readHandle.seek(offset)
                d.update(readHandle.read(length))

        completed = (d.digest() == self.metainfo.getHash(pieceIndex))
        if completed:
            self.completed.append(piece)
        return completed
           

class FileStorage(object):
    """
    File storage that stores the content in a single file.
    
    @ivar completed: C{list} of indexes of completed pieces.
    """
    implements(IStorage)

    def __init__(self, filename, totalSize, metainfo):
        self.metainfo = metainfo
        self.filename = filename
        self.totalSize = totalSize
        self.completed = set()
        self.readHandle = None
        self.writeHandle = None

    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['readHandle']
        del odict['writeHandle']
        return odict

    def __setstate__(self, idict):
        self.__dict__ = idict
        self.readHandle = None
        self.writeHandle = None
        
    def getReadHandle(self):
        """
        Return file handle for reading the file.
        """
        if self.readHandle is not None:
            return self.readHandle
        
        try:
            self.readHandle = open(self.filename, 'r')
        except IOError:
            return None
        
        return self.readHandle

    def getWriteHandle(self):
        """
        Return write handle.
        """
        if self.writeHandle is not None:
            return self.writeHandle

        try:
            if os.path.exists(self.filename):
                self.writeHandle = open(self.filename, 'rb+')
            else:
                self.writeHandle = open(self.filename, 'w+')
        except IOError:
            dirname = os.path.dirname(self.filename)
            if dirname:
                try:
                    os.makedirs(dirname)
                except OSError:
                    pass
            self.writeHandle = open(self.filename, 'w+')

        # FIXME: should we allocate the file here?
        return self.writeHandle
        
    def done(self):
        """
        Return C{True} if this storage has all content.
        """
        return len(self.completed) == self.metainfo.numPieces

    def getNumberCompleted(self):
        """
        Returns the number of completed pieces in the storage.
        """
        return len(self.completed)

    def iterCompletedPieces(self):
        """
        Returns a iterator that will iterate through all currently
        completed pieces.
        """
        return iter(self.completed)

    def have(self, piece):
        """
        Return C{True} if the specified piece is in the storage.
        """
        return piece in self.completed

    def check(self, progress=lambda x: None):
        """
        Check any preexisting content of the file and build an index
        of what pieces already exists.

        Returns a deferred that will be called when the checking is
        done.

        @param progress: a single argument function that will be
            called throughout the checking, with progress information
            in the interval [0, 1)
        """
        def _check():
            readHandle = self.getReadHandle()
            if readHandle is not None:
                readHandle.seek(0)
                progress(0.0)
                for c in range(self.metainfo.numPieces):
                    low = self.metainfo.pieceSize * c
                    high = low + self.metainfo.pieceSize
                    if high > self.totalSize:
                        high = self.totalSize

                    d = readHandle.read(high - low)
                    if (len(d) != (high - low)):
                        pass
                    elif digest(d) == self.metainfo.getHash(c):
                        self.completed.add(c)
                    progress(c / float(self.metainfo.numPieces))
                    yield None
                progress(1.0)
        return task.coiterate(_check())

    def write(self, piece, offset, data):
        """
        Write chunk data to storage and return C{True} if this chunk
        completed the piece.

        @param piece: piece index
        @param offset: offset in piece
        @param data: chunk data
        """
        pos = piece * self.metainfo.pieceSize
        
        writeHandle = self.getWriteHandle()
        writeHandle.seek(pos + offset)
        writeHandle.write(data)

        # read it back and check if the piece was complete
        readHandle = self.getReadHandle()
        readHandle.seek(pos)
        completed = (digest(readHandle.read(self.metainfo.pieceSize))
                     == self.metainfo.getHash(piece))
        if completed:
            self.completed.add(piece)
        return completed

    def read(self, piece, offset, length):
        """
        Read content for a chunk of a piece.
        
        @param offset: offset of chunk
        @param length: length of chunk
        """
        readHandle = self.getReadHandle()
        if readHandle is None:
            raise IOError("no read handle")
        readHandle.seek(piece * self.metainfo.pieceSize + offset)
        return readHandle.read(length)
