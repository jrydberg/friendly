from twisted.internet import task
from overlay.utils import randbytes


class SimplestProbeManager(task.LoopingCall):
    """
    The probe managers solo task is to try to find virtual paths that
    terminate the probe.  
    """

    def __init__(self, controller, q, factory):
        task.LoopingCall.__init__(self, self.probe)
        self.controller = controller
        self.q = q
        self.factory = factory
        self.cid = randbytes(20)
        self.sid = None

    def start(self):
        task.LoopingCall.start(self, 15, True)
        
    def stop(self):
        if self.sid is not None:
            self.controller.removeProbeManager(self.sid)
        task.LoopingCall.stop(self)

    def probe(self):
        if self.sid is not None:
            self.controller.removeProbeManager(self.sid)
        self.sid = randbytes(20)
        self.controller.addProbeManager(self.sid, self)
        #print "Peer", self.controller.i, "does a probe"
        for connection in self.controller.connections.itervalues():
            connection.sendPROBE(self.q, self.cid, self.sid, 10, None)
        
    def accept(self, address):
        #print "Asking probe manager to access", address
        return self.factory.buildProtocol(address)
