from twisted.internet import main, reactor
from overlay.utils import randbytes, LoopingCall
from overlay.address import OverlayAddress
from overlay.log import logger_controller as log
from overlay.utils import short_hash
import time, sha

# Remaing to do is to let OverlayController not raise ValueError, but
# some other exception; AlreadyConnectedError maybe.


def build_terminate_path_id(q, connection):
    return sha.sha(q + connection.connection_id).digest()


def build_path_id(q, connection):
    return sha.sha(q + connection.connection_id).digest()


def pretty(d):
    s = ':'.join([('%02x' % ord(v)) for v in d])
    return s[:5] + '...' + s[-5:]


class DuplicateProbeError(Exception):
    """
    The probe has already been received.
    """
    

class ProbeTable(LoopingCall):
    """
    The probe table hold all probe related state. 

    Logically it is a mapping between a session id the interface from
    where the probe was received.
    """

    def __init__(self, interval, clock):
        LoopingCall.__init__(self, clock, self.prune)
        self.sid_mapping = dict()
        self.con_mapping = dict()
        self.time_list = list()
        clock.callLater(0, self.start, interval, False)
        
    def connectionLost(self, connection):
        """
        Notify the table that connection has been lost to the
        specified connection, and all state related to the connection
        should be pruned.

        @type connection: L{IConnection}
        """
        if not connection in self.con_mapping:
            return
        for sid in self.con_mapping[connection]:
            del self.sid_mapping[sid]
        del self.con_mapping[connection]

    def prune(self):
        """
        Prune old searches from the table.
        """
        n = self.clock.seconds()
        # FIXME: there has to be a better way to do this:
        c = 0
        while c < len(self.time_list) \
                  and n > (self.time_list[c][1] + self.interval):
            sid, t = self.time_list[c]
            try:
                connection = self.sid_mapping.pop(sid)
                self.con_mapping[connection].remove(sid)
            except KeyError:
                # the entry has already been pruned
                pass
            c += 1
        self.time_list = self.time_list[c:]

    def get(self, sid):
        """
        Return connection that probe with the specified session id was
        received from.

        Returns L{None} if no such mapping was available.

        @rtype: L{IConnection}
        """
        return self.sid_mapping.get(sid, None)
        
    def add(self, sid, connection):
        """
        Add a mapping between the specified session id and the
        given connection.

        May raise L{DuplicateProbeError} if theres already a mapping
        for that session id in table.

        @type sid: 20-byte L{str}
        @type connection: L{IConnection}
        """
        if sid in self.sid_mapping:
            raise DuplicateProbeError(sid)
        self.sid_mapping[sid] = connection
        self.time_list.append((sid, self.clock.seconds()))
        if connection not in self.con_mapping:
            self.con_mapping[connection] = list()
        self.con_mapping[connection].append(sid)


class ProbePolicy:
    """
    The probe policy is all about doing smart disitrbution of the
    probes throughout the network.
    """

    def __init__(self, controller):
        self.controller = controller

    def connectionLost(self, connection):
        """
        Notify the probe policy that the specified connectio has been
        lost and that it has to remove any state it has about the
        connection.
        """

    def establish(self, target, target_pid, cid, sid, source):
        """
        Ask the probe policy if it is OK to establish a path between
        target and source connections with the given target pid.

        The path is the result of a probe with session id L{sid}.

        @return: False if path should not be established.
        """
        return True
        
    def probe(self, q, cid, sid, ttl, source):
        """
        Relay a probe on the behalf of connection.
        """
        log.debug('possible relay targets:')
        for target in self.controller.connections.itervalues():
            log.debug('  %s', target.getFriend())
        for target in self.controller.connections.itervalues():
            if target is not source:
                target_pid = build_path_id(cid, target)
                log.info('relaying probe to %s pid:%s sid:%s ttl:%d',
                         target.getFriend(), short_hash(target_pid),
                         short_hash(sid), ttl - 1)
                target.sendPROBE(
                    q, build_path_id(cid, target), sid, ttl - 1, source
                    )


class NoRouteError(Exception):
    """
    No route entry available.
    """


class RoutingTable(LoopingCall):
    """Routing table.

    The table acts as a homogenous mapping where the key and mapping
    is a tuple of connection and path identifier.
    """

    # FIXME: this is a very simple implementation

    def __init__(self, clock):
        LoopingCall.__init__(self, clock, self.prune)
        self.entries = dict()
        clock.callLater(0, self.start, 30, False)

    def inspect(self):
        for (sc, spid), (tc, tpid, t) in self.entries.iteritems():
            print "    ", sc.getFriend(), ",", pretty(spid), " -> ", tc.getFriend(), ",", pretty(tpid)
        
    def connectionLost(self, connection):
        """
        Prune all route entries that go along the specified
        connection.
        """
        l = list()
        for (sc, spid), (tc, tpid, t) in self.entries.iteritems():
            if sc is connection or tc is connection:
                l.append((sc, spid))
        for c, pid in l:
            del self.entries[c, pid]

    def delete(self, connection, pid):
        """
        Delete routing entries for the specified source route.
        """
        try:
            e = self.entries[connection, pid]
        except KeyError:
            return NoRouteEntry(connection, pid)
        del self.entries[connection, pid]
        del self.entries[e[0], e[1]]
        return e[0], e[1]
        
    def get(self, connection, pid):
        """
        Lookup routing entry for the specified connection and path
        and return target connection and path id.
        """
        try:
            e = self.entries[connection, pid]
        except KeyError:
            raise NoRouteError(connection, pid)
        self._touch(connection, pid)
        self._touch(e[0], e[1])
        return e[0], e[1]

    def add(self, source, spid, target, tpid):
        """
        Add a routing entry.
        """
        now = self.clock.seconds()
        self.entries[source, spid] = [target, tpid, now]
        self.entries[target, tpid] = [source, spid, now]

    def _touch(self, c, pid):
        self.entries[c, pid][2] = self.clock.seconds()

    def prune(self):
        """
        Prune idle paths.
        """
        l = list()
        now = self.clock.seconds()
        for (sc, spid), (tc, tpid, t) in self.entries.iteritems():
            if now > (t + self.interval):
                l.append((sc, spid))
        for c, pid in l:
            log.info('delete route entry pid:%s via %s',
                     short_hash(pid), c.getFriend())
            del self.entries[c, pid]

            
class Transport:

    def __init__(self, connection, q, pid, cid, controller):
        self.connection = connection
        self.q = q
        self.pid = pid
        self.cid = cid
        self.controller = controller
        self.protocol = None
        
    def sendMessage(self, opcode, data):
        """
        Send an application message along the path.

        @param opcode: message opcode
        @param data: message payload
        """
        assert opcode >= 0x80, "non-app opcode"
        self.controller.sendAppMessage(
            self.connection, self.pid, self.cid, opcode, data
            )
        
    def messageReceived(self, opcode, data):
        """
        Pass message along to protcol implementation.

        @param opcode: message opcode
        @param data: message payload
        """
        assert self.protocol is not None
        self.protocol.messageReceived(opcode, data)

    def connectionLost(self, reason=main.CONNECTION_LOST):
        """
        Connection to remote peer has lost.
        """
        if self.protocol is not None:
            self.protocol.connectionLost(reason)

    def loseConnection(self):
        """
        Lose connection.
        """
        # FIXME: send CONNECTION_DONE to our transport
            

class OverlayController:
    """
    Overlay Controller.
    """

    def __init__(self, i, connector, factory, clock=reactor):
        self.i = i
        self.factory = factory
        self.connections = dict()
        self.connector = connector
        self.policy = ProbePolicy(self)
        self.ptable = ProbeTable(15, clock)
        self.managers = dict()
        self.rtable = RoutingTable(clock)
        self.transports = dict()
        self.paths = 0
        
    def connectionMade(self, connection):
        if connection.getFriend() in self.connections:
            raise ValueError("duplicate")
        self.connections[connection.getFriend()] = connection
        self.connector.connectionMade(connection)

    def connectionLost(self, connection):
        del self.connections[connection.getFriend()]
        self.connector.connectionLost(connection)
        self.ptable.connectionLost(connection)
        try:
            transports = self.transports.pop(connection)
        except KeyError:
            pass
        else:
            for transport in transports.itervalues():
                transport.connectionLost()
            
    # ProbeManager:
    def addProbeManager(self, sid, pm):
        log.debug('add probe manager for %s', pretty(sid))
        self.managers[sid] = pm

    def removeProbeManager(self, sid):
        log.debug('remove probe manager for %s', pretty(sid))
        del self.managers[sid]

    # Outbound:
    def sendAppMessage(self, target, pid, cid, opcode, data):
        target.sendAppMessage(pid, cid, opcode, data, None)

    # Inbound:
    def receivedPROBE(self, q, cid, sid, ttl, source):
        """
        Process incoming probe request. The probe was recevied on
        L{source}.

        @param sid: session identifier
        @param q: query
        @param ttl: time to live
        """
        log.info('received PROBE from %s with sid:%s cid:%s',
                 source.getFriend(), short_hash(sid), short_hash(cid))
        
        if sid in self.managers:
            # If the probe originated from this node and we get the probe
            # back to ourselves we simply drop it. This is quite common,
            # since me and my friends have friends incommon.
            log.debug('probe killed because cycle in the network')

        elif self.factory.terminatesProbe(q):
            # This node happened to terminate the search.  Build a
            # determenistic path identifier and get a new random
            # channel identifier.
            pid = build_terminate_path_id(q, source)

            log.info('probe terminated!')
            
            # Check if the path already exists.  If so, theres no need
            # to create a new one.
            if not source in self.transports:
                self.transports[source] = dict()
            if (pid, cid) in self.transports[source]:
                # FIXME: maybe we should still send out an establish.
                # this could be a re-establish, right?  that way, the
                # keep-alives is done through the probe engine.
                log.debug('probe killed because path already exists')
                source.sendESTABLISH(pid, cid, sid, None)
                return
            
            # Create a new transport for the path, but do not attach a
            # protocol to it at this point. That is done when the
            # first application message is received through the path.
            transport = Transport(source, q, pid, cid, self)
            self.transports[source][pid, cid] = transport
            
            # Send back the establish message on the same connection
            # it arrived on.
            log.info('establish new path pid:%s cid:%s via %s',
                     short_hash(pid), short_hash(cid), source.getFriend())
            source.sendESTABLISH(pid, cid, sid, None)

        elif ttl < 2 or ttl > 15:
            log.debug('probe killed because of the ttl')
        else:
            try:
                self.ptable.add(sid, source)
            except DuplicateProbeError:
                log.debug('probe killed because it was a duplicate')
                return
            self.policy.probe(q, cid, sid, ttl, source)

    def receivedAppMessage(self, pid, cid, opcode, data, source):
        """
        Process incoming application message.

        @param pid: path identifier
        @param cid: channel identifier
        @param opcode: message opcode
        @param data: message payload
        @param source: source connection
        """
        log.info('received app message (%x l:%d) on pid:%s cid:%s from %s',
                 opcode, len(data), short_hash(pid), short_hash(cid),
                 source.getFriend())
        if source in self.transports and (pid, cid) in self.transports[source]:
            transport = self.transports[source][pid, cid]
            if transport.protocol is None:
                # There is no protocol associated with the transport, because
                # we do not build protocols before the originator has accepted
                # the channel.
                log.debug('building protocol for existing transport')
                address = OverlayAddress(transport.q, pid, cid, source.getFriend())
                transport.protocol = self.factory.buildProtocol(address)
                # FIXME: check protocol here!
                transport.protocol.makeConnection(transport)
                self.paths += 1
            log.debug('deliver message to transport')
            transport.messageReceived(opcode, data)
            return

        try:
            target, target_pid = self.rtable.get(source, pid)
        except NoRouteError:
            # FIXME: invoke bad-behavior tracker here
            log.info('sending RESET pid:%s cid:%s', short_hash(pid),
                     short_hash(cid))
            source.sendRESET(pid, cid, None)
        else:
            # FIXME: invoke cacher here
            log.info('forwarding app message pid:%s cid:%s',
                     short_hash(target_pid), short_hash(cid))
            target.sendAppMessage(target_pid, cid, opcode, data, source)

    def inspect(self):
        print "Inspection of", self.i
        for connection, d in self.transports.iteritems():
            print "  connections to:", connection.getFriend()
            for (pid, cid), transport in d.iteritems():
                print "     ", pretty(pid), ",", pretty(cid)
        self.rtable.inspect()
                
    def receivedESTABLISH(self, pid, cid, sid, source):
        """
        Process incomming establish message.

        @param pid: path identifier
        @param cid: channel identifier
        @param opcode: message opcode
        @param data: message payload
        @param source: source connection
        """
        log.info('received ESTABLISH from %s with pid:%s cid:%s sid:%s',
                 source.getFriend(), short_hash(pid), short_hash(cid),
                 short_hash(sid))
        if sid in self.managers:
            log.info('probe originated from this node')
            
            # Sort out already established paths;
            if source in self.transports \
                    and (pid, cid) in self.transports[source]:
                log.debug('path was already established in this node')
                return

            log.debug('build transport and protocol')

            # Let the probe manager accept the newly established path.
            # FIXME: better way to get hold of "q"
            address = OverlayAddress(self.managers[sid].q, pid, cid,
                                     source.getFriend())
            protocol = self.managers[sid].accept(address)
            if protocol is None:
                log.info('sending RESET with pid:%s cid:%s',
                         short_hash(pid), short_hash(cid))
                source.sendRESET(pid, cid)
                return

            self.paths += 1

            # Create a transport and hook it to the protocol and to
            # the connection.
            transport = Transport(source, address.q, pid, cid, self)
            if not source in self.transports:
                self.transports[source] = dict()
            self.transports[source][pid, cid] = transport
            transport.protocol = protocol
            protocol.makeConnection(transport)
        else:
            target = self.ptable.get(sid)
            if target is None:
                log.info('session not in probe table')
                return

            target_pid = build_path_id(pid, target)
            if not self.policy.establish(target, target_pid, cid, sid, source):
                # the probe policy decided to NOT establish this path
                # through this controller.
                # FIXME: should this be sent on the behalf of target?
                log.info('send RESET pid:%s cid:%s', short_hash(pid),
                         short_hash(cid))
            else:
                self.rtable.add(source, pid, target, target_pid)
                log.info('send ESTABLISH pid:%s cid:%s sid:%s to %s',
                         short_hash(target_pid), short_hash(cid),
                         short_hash(sid), target.getFriend())
                target.sendESTABLISH(target_pid, cid, sid, source)

    def receivedRESET(self, pid, cid, source):
        """
        Process incomming RESET message.

        @param pid: path id
        @param cid: channel id
        @param source: connection that sent the message
        """
        log.info('received RESET from %s with pid:%s cid:%s',
                 source.getFriend(), short_hash(pid), short_hash(cid))
        if source in self.transports \
                and (pid, cid) in self.transports[source]:
            log.info('transport connection lost')
            self.transports[source].pop((pid, cid)).connectionLost()
        else:
            try:
                target, target_pid = self.rtable.delete(source, pid)
            except NoRouteError:
                log.debug('no such route entry')
                return
            log.info('sending RESET pid:%s cid:%s to %s',
                     short_hash(target_pid), short_hash(cid),
                     source.getFriend())
            target.sendRESET(target_pid, cid, source)
