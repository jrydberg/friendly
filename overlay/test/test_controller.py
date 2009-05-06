# Written by Johan Rydberg <johan.rydberg@gmail.com>

from twisted.trial import unittest
from twisted.internet.task import Clock
from overlay.controller import (ProbeTable, RoutingTable,
                                NoRouteError, OverlayController)
from overlay import factory, utils, controller


class TestFriend:

    def __init__(self):
        self.id = id(self)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return other.id == self.id


class TestConnection:

    def __init__(self):
        self.events = list()
        self.friend = TestFriend()
        self.connection_id = utils.randbytes(20)

    def __hash__(self):
        return hash(id(self))

    def sendESTABLISH(self, pid, cid, sid, flow):
        self.events.append(('establish', pid, cid, sid))

    def sendPROBE(self, q, cid, sid, ttl, flow):
        self.events.append(('probe', q, cid, sid, ttl))

    def sendAppMessage(self, pid, cid, opcode, data, flow):
        self.events.append(('app', pid, cid, opcode, data))

    def sendRESET(self, pid, cid, flow):
        self.events.append(('reset', pid, cid))
        
    def getFriend(self):
        return self.friend

        
def advance(c, n):
    for i in range(n):
        c.advance(1)


class ProbeTableTest(unittest.TestCase):

    def setUp(self):
        self.clock = Clock()
        self.table = ProbeTable(5, self.clock)

    def test_connectionLost(self):
        """
        Verify that all state for a connection is pruned when the
        connection is lost.
        """
        c1 = TestConnection()
        c2 = TestConnection()
        self.table.add('1', c1)
        self.table.add('6', c1)
        self.table.add('2', c2)
        self.assertTrue(self.table.get('1') is c1)
        self.assertTrue(self.table.get('6') is c1)
        self.assertTrue(self.table.get('2') is c2)
        self.table.connectionLost(c1)
        self.assertTrue(self.table.get('6') is None)
        self.assertTrue(self.table.get('1') is None)
        self.assertTrue(self.table.get('2') is c2)

    def test_pruneLostEntries(self):
        """
        Verify that the pruner can handle already deleted entries.
        """
        c1 = TestConnection()
        c2 = TestConnection()
        self.table.add('1', c1)
        self.table.add('2', c2)
        self.table.connectionLost(c1)
        advance(self.clock, 10)
        self.assertTrue(self.table.get('1') is None)
        self.assertTrue(self.table.get('2') is None)
        self.assertEquals(len(self.table.time_list), 0)
        self.assertEquals(len(self.table.con_mapping), 1)
        self.assertEquals(len(self.table.sid_mapping), 0)

    def test_pruneKeepActiveEntries(self):
        """
        Verify that the pruner doesnt remove everything-
        """
        c1 = TestConnection()
        c2 = TestConnection()
        self.table.add('1', c1)
        advance(self.clock, 3)
        self.table.add('2', c2)
        advance(self.clock, 3)
        self.assertTrue(self.table.get('1') is None)
        self.assertTrue(self.table.get('2') is not None)

    # TODO: write test entry for duplicate entry


class RoutingTableTest(unittest.TestCase):

    def setUp(self):
        self.clock = Clock()
        self.table = RoutingTable(self.clock)

    def test_noRouteError(self):
        """
        Verify that NoRouteError is raised when there is no routing
        entry available.
        """
        c = TestConnection()
        def test():
            self.table.get(c, 'pid')
        self.assertRaises(NoRouteError, test)

    def test_connectionLost(self):
        """
        Verify that routing entries are pruned when a connection is
        lost.
        """
        c1 = TestConnection()
        c2 = TestConnection()
        c3 = TestConnection()
        self.table.add(c1, 'A1', c2, 'X1')
        self.table.add(c1, 'A2', c3, 'X2')
        self.table.add(c3, 'A3', c2, 'X3')
        self.table.connectionLost(c2)
        def test(c, pid):
            self.table.get(c, pid)
        self.assertRaises(NoRouteError, test, c1, 'A1')
        self.assertRaises(NoRouteError, test, c2, 'X1')
        self.assertRaises(NoRouteError, test, c3, 'A3')
        self.assertRaises(NoRouteError, test, c2, 'X3')
        self.assertEquals(self.table.get(c1, 'A2'), (c3, 'X2'))
        self.assertEquals(self.table.get(c3, 'X2'), (c1, 'A2'))

        
class TestConnector:

    def connectionMade(self, connection):
        pass

    def connectionLost(self, connection):
        pass


class TestFactory(factory.OverlayFactory):

    def __init__(self):
        self.q = list()

    def add(self, e):
        self.q.append(e)

    def terminatesProbe(self, q):
        return q in self.q

    def buildProtocol(self, address):
        """
        """
        print "build protocol"
        
    
class ControllerTest(unittest.TestCase):

    def setUp(self):
        self.clock = Clock()
        self.factory = TestFactory()
        self.controller = OverlayController("x", TestConnector(),
                                            self.factory, self.clock)

    def test_networkCycleKillsProbe(self):
        """
        Verify that probes are killed when a cycle (originator
        receives its own probe) in the network is detected.
        """
        c1 = TestConnection()
        c2 = TestConnection()
        self.controller.connectionMade(c1)
        self.controller.connectionMade(c2)
        sid = '\2' * 20
        q   = '\0' * 20
        self.controller.managers[sid] = True
        self.controller.receivedPROBE(q, q, sid, 1, c1)
        self.assertEquals(len(c2.events), 0)

    def test_tileToLiveKillsProbe(self):
        """
        Verify that probes are killed when the TTL says so.
        """
        c1 = TestConnection()
        c2 = TestConnection()
        self.controller.connectionMade(c1)
        self.controller.connectionMade(c2)
        sid = '\2' * 20
        q   = '\0' * 20
        self.controller.receivedPROBE(q, q, sid, 1, c1)
        self.assertEquals(len(c2.events), 0)

    def test_duplicateKillsProbe(self):
        """
        Verify that duplicate probes are recognized.
        """
        c1 = TestConnection()
        c2 = TestConnection()
        c3 = TestConnection()
        self.controller.connectionMade(c1)
        self.controller.connectionMade(c2)
        self.controller.connectionMade(c3)
        sid = '\2' * 20
        q   = '\0' * 20
        self.controller.receivedPROBE(q, q, sid, 3, c1)
        self.assertEquals(len(c2.events), 1)
        self.controller.receivedPROBE(q, q, sid, 2, c3)
        self.assertEquals(len(c2.events), 1)

    def test_terminatingProbeCreatesTransport(self):
        """
        Verify that a transport is created and that an establish
        message is return for terminating probes.
        """
        sid = '\2' * 20
        q   = '\0' * 20
        c1 = TestConnection()
        c2 = TestConnection()
        self.controller.connectionMade(c1)
        self.controller.connectionMade(c2)
        self.factory.add(q)
        self.controller.receivedPROBE(q, q, sid, 3, c1)
        self.assertEquals(len(c1.events), 1)
        self.assertEquals(len(self.controller.transports), 1)
        transports = self.controller.transports[c1]
        self.assertEquals(len(transports), 1)
        transport = transports[transports.keys()[0]]
        pid = controller.build_terminate_path_id(q, c1)
        self.assertEquals(transport.pid, pid)
        self.assertEquals(transport.cid, q)
        self.assertEquals(transport.protocol, None)

    def test_makeVirtualPath(self):
        # FIXME: rewrite this test, or clean it up at least
        sid = '\2' * 20
        q   = '\0' * 20
        c1 = TestConnection()
        c2 = TestConnection()
        pid = '\3' * 20
        self.controller.connectionMade(c1)
        self.controller.connectionMade(c2)
        self.controller.receivedPROBE(q, q, sid, 3, c1)
        self.assertEquals(len(c2.events), 1)
        self.controller.receivedESTABLISH(pid, pid, sid, c2)
        self.assertEquals(len(c1.events), 1)
        source_pid, cid = c1.events[0][1:3]
        # verify that a message can be routed through the path.
        self.controller.receivedAppMessage(source_pid, cid, 0x80,
                                           'hello', c1)
        self.assertEquals(len(c2.events), 2)
        self.assertEquals(c2.events[1][0], 'app')
        self.assertEquals(c2.events[1][1:3], (pid, cid))
        
    def test_noRouteSendsReset(self):
        """
        Verify that trying to route a message through a node that has
        no record of that path returns a RESET message.
        """
        c1 = TestConnection()
        pid = '\3' * 20
        cid = '\2' * 20
        self.controller.connectionMade(c1)
        self.controller.receivedAppMessage(pid, cid, 0x80, 'hello', c1)
        self.assertEquals(len(c1.events), 1)
        self.assertEquals(c1.events[0][0], 'reset')

    def test_resetDeletesPath(self):
        """
        Verify that a received RESET message deletes the routing
        entries and propagates the reset.
        """
        sid = '\2' * 20
        q   = '\0' * 20
        c1 = TestConnection()
        c2 = TestConnection()
        pid = '\3' * 20
        self.controller.connectionMade(c1)
        self.controller.connectionMade(c2)
        self.controller.receivedPROBE(q, q, sid, 3, c1)
        self.assertEquals(len(c2.events), 1)
        self.controller.receivedESTABLISH(pid, pid, sid, c2)
        self.assertEquals(len(c1.events), 1)
        source_pid, cid = c1.events[0][1:3]
        # verify that a message can be routed through the path.
        self.controller.receivedRESET(source_pid, cid, c1)
        self.assertEquals(len(c2.events), 2)
        self.assertEquals(c2.events[1][0], 'reset')
        self.assertEquals(c2.events[1][1], pid)
