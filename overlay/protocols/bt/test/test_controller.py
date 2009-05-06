from twisted.trial import unittest
from overlay.protocols.bt import controller, picker, schedule


class TestChoker:

    def connectionMade(self, connection):
        pass

    def connectionLost(self, connection):
        pass


class TestConnection:

    def __init__(self, name):
        self._name = name
        self._pending = list()
        self._events = list()
        self._choked = True
        self._interested = False
        self._choking = True
        self._interesting = False
        self._pieces = list()

    def pieces(self):
        return self._pieces

    def sendInteresting(self):
        if not self._interesting:
            self._interesting = True
            self._events.append(('interesting',))

    def sendNotInteresting(self):
        if self._interesting:
            self._interesting = False
            self._events.append(('not interesting',))

    def interesting(self):
        return self._interesting

    def have(self, i):
        return i in self._pieces

    def pending(self):
        return self._pending

    def choked(self):
        return self._choked

    def request(self, piece, offset, length):
        self._events.append(('req', piece, offset, length))
        self._pending.append((piece, offset, length))

    def sendPiece(self, controller, i=None):
        if i is None:
            i = 0
        e = self._pending.pop(i)
        controller.requestHonored(self, e[0], e[1], 'a')

    def sendHave(self, piece):
        self._events.append(('have', piece))

    def __str__(self):
        return self._name

    __repr__ = __str__
        

class TestStorage:

    def __init__(self):
        self._completed = list()

    def write(self, piece, offset, data):
        return piece in self._completed

    def _complete(self, piece):
        return piece in self._completed

    def num(self):
        return 0


class TestSchedule(schedule.Schedule):

    def __init__(self, num):
        self.num = num
        self.pending = [None] * num
        for i in range(num):
            self.pending[i] = list()
            for c in range(2):
                self.pending[i].append(((c * 1), 1))
        self.active = [None] * num


class ControllerTest(unittest.TestCase):

    def setUp(self):
        self.storage = TestStorage()
        self.schedule = TestSchedule(6)
        self.choker = TestChoker()
        self.picker = picker.PiecePicker(6)
        self.controller = controller.Controller(self.choker,
                                                self.schedule,
                                                self.storage,
                                                self.picker,
                                                backlog=1)
        self.c1 = TestConnection('c1')
        self.c2 = TestConnection('c2')

    def unchoke(self, connection):
        connection._choked = False
        self.controller.requestMore(connection)

    def test_doesNotRequestWhenChoked(self):
        """
        Verify that we do not request chunks we choked.
        """
        self.controller.connectionMade(self.c1)
        self.controller.connectionMade(self.c2)
        self.c1._pieces.extend([0])
        self.controller.gotHave(self.c1, [0])
        self.assertEquals(len(self.c1._events), 1)
        self.assertEquals(self.c1._events[0][0], 'interesting')
        # unchoke c1
        self.unchoke(self.c1)
        self.assertEquals(len(self.c1._events), 2)
        self.assertTrue(self.c1._events[1] == ('req', 0, 0, 1))

    def test_requestMoreDoesNotRequestMore(self):
        """
        Verify that requestMore does not request more if the
        connection has its backlog full.
        """
        self.controller.connectionMade(self.c1)
        self.c1._pieces.extend([0, 5])
        self.controller.gotHave(self.c1, [0, 5])
        self.c1._choked = False
        self.controller.requestMore(self.c1)
        self.assertEquals(len(self.c1._events), 2)
        self.controller.requestMore(self.c1)
        self.assertEquals(len(self.c1._events), 2)

    def test_sendHaveWhenPieceIsCompleted(self):
        """
        Verify that HAVE messages are send out when a piece is
        completed.
        """
        self.controller.setBacklog(2)
        self.controller.connectionMade(self.c1)
        self.controller.connectionMade(self.c2)
        self.c1._pieces.extend([0])
        self.controller.gotHave(self.c1, [0])
        self.unchoke(self.c1)
        self.assertEquals(len(self.c1._events), 3)
        self.assertEquals(self.c1._events[0], ('interesting',))
        self.assertEquals(self.c1._events[1], ('req', 0, 0, 1))
        self.assertEquals(self.c1._events[2], ('req', 0, 1, 1))
        self.c1.sendPiece(self.controller)
        self.storage._completed.append(0)
        self.c1._pieces.append(0)
        self.c1.sendPiece(self.controller)
        self.assertEquals(self.c1._events[3], ('have', 0))
        self.assertEquals(self.c1._events[4], ('not interesting',))

    def test_rejectedRequestsRerequested(self):
        """
        Verify that if the connection ot a peer is lost while there's
        pending requests to that peer, that these requests are sent to
        other peers.
        """
        self.controller.setBacklog(2)
        self.controller.connectionMade(self.c1)
        self.controller.connectionMade(self.c2)
        self.c1._pieces.extend([0])
        self.controller.gotHave(self.c1, [0])
        self.unchoke(self.c1)
        self.assertEquals(len(self.c1._events), 3)
        self.assertEquals(self.c1._events[0], ('interesting',))
        self.assertEquals(self.c1._events[1], ('req', 0, 0, 1))
        self.assertEquals(self.c1._events[2], ('req', 0, 1, 1))
        self.c2._pieces.extend([0])
        self.controller.gotHave(self.c2, [0])
        self.assertEquals(len(self.c2._events), 0)
        self.controller.connectionLost(self.c1)
        self.controller.requestsRejected(self, self.c1._pending)
        self.assertEquals(len(self.c2._events), 1)
        self.assertEquals(self.c2._events[0], ('interesting',))
        self.unchoke(self.c2)
        self.assertEquals(len(self.c2._events), 3)

    def test_checkLostInterestNoMorePieces(self):
        """
        Verify that interest is lost when there are no more pieces
        available at the peer that we are interested in.
        """
        self.controller.connectionMade(self.c1)
        self.c1._pieces.extend([0])
        self.c1._interesting = True
        self.schedule.pending[0] = list()
        self.controller.checkLostInterest(self.c1, [0])
        self.assertEquals(self.c1._events[0], ('not interesting',))

    def test_checkLostInterestMorePieces(self):
        """
        Verify that that interest is kept if there are still pieces
        available that we are interested in.
        """
        self.controller.connectionMade(self.c1)
        self.c1._pieces.extend([0, 4])
        self.c1._interesting = True
        self.schedule.pending[0] = list()
        self.controller.checkLostInterest(self.c1, [0])
        self.assertEquals(len(self.c1._events), 0)

    def test_checkLostInterestNoPieces(self):
        self.controller.connectionMade(self.c1)
        self.c1._interesting = True
        self.schedule.pending[0] = list()
        self.controller.checkLostInterest(self.c1, [0])
        self.assertEquals(len(self.c1._events), 1)
        self.assertEquals(self.c1._events[0], ('not interesting',))
        

