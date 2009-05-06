from twisted.trial import unittest
from overlay.protocols.bt.storage import MultiFileStorage

class MetaInfo:

    def __init__(self, n, ps):
        self.n = n
        self.piecesize = ps

    def num(self):
        return n


class MultiFileStorageTestCase(unittest.TestCase):

    def setUp(self):
        self.metainfo = MetaInfo(7, 1024)
        filelist = (
            ('a', 1024),
            ('b', 4000),
            ('c', 1),
            ('d', 95),
            ('e', 100),
            )
        self.storage = MultiFileStorage(self.metainfo, filelist)

    def test_singleFileInInterval(self):
        intervals = list(self.storage.getIntervals(0, 0, 1024))
        self.assertEquals(intervals[0], ('a', 0, 1024))
        self.assertEquals(len(intervals), 1)

    def test_insideBodyOfFile(self):
        intervals = list(self.storage.getIntervals(1, 0, 1024))
        self.assertEquals(intervals[0], ('b', 0, 1024))
        self.assertEquals(len(intervals), 1)

    def test_multipleSpanning(self):
        intervals = list(self.storage.getIntervals(4, 0, 1024))
        self.assertEquals(intervals[0], ('b', 3072, 928))
        self.assertEquals(intervals[1], ('c', 0, 1))
        self.assertEquals(intervals[2], ('d', 0, 95))
        self.assertEquals(len(intervals), 3)

    def test_endIsCropped(self):
        intervals = list(self.storage.getIntervals(5, 0, 1024))
        self.assertEquals(intervals[0], ('e', 0, 100))
        self.assertEquals(len(intervals), 1)
