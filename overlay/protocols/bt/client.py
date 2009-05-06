# Copyright (C) 2009 Johan Rydberg <johan.rydberg@gmail.com>
# See LICENSE.txt for information on what you may and may not do with
# this code.

from overlay.protocols.bt.connector import Connector
from overlay.protocols.bt.choker import Choker
from overlay.protocols.bt.schedule import Schedule
from overlay.protocols.bt.picker import Picket
from overlay.protocols.bt.controller import Controller
from overlay.protocols.bt.factory import ClientFactory

CHUNKSIZE = 16*1024


# TODO:
# Remaining to do is to figure out how to separate existing protocol
# instances, so that all connections for an overlay can be closed when
# it is detached,


class Client:
    """
    C{Client} encapsulates all the functionality needed to transfer a
    the share unit over one or serveral overlays.

    @ivar controller: The file transfer protocol controller.
    @type controller: L{overlay.protocols.bt.controller.Controller}
    """

    def __init__(self, storage, metainfo, chunksize=CHUNKSIZE):
        self.running = False
        self.storage = storage
        self.metainfo = metainfo
        self.connectors = list()
        self.choker = Choker()
        self.picker = PiecePicker(self.metainfo.numPieces)
        self.schedule = Schedule(self.storage, self.metainfo, chunksize)
        self.controller = Controller(
            self.choker, self.schedule, self.storage, self.picker
            )
        self.factory = ClientFactory(self.controller, self.metainfo)

    def getDelegate(self):
        """
        Return the current delegate.
        """
        return self.controller.getDelegate()
        
    def setDelegate(self, delegate):
        """
        Set delegate.

        @param delegate: the new delegate.
        """
        self.controller.setDelegate(delegate)
        
    def iterConnections(self):
        """
        Iterate through all connections.

        @return: an iterator for all connections.
        """
        return iter(self.controller.connections)
        
    def addOverlay(self, overlay):
        """
        Attach this client to the specified overlay.

        @param overlay: overlay controller
        @type  overlay: L{overlay.controller.Controller}
        """
        conenctor = Connector(overlay, self.metainfo.rootHash, self.factory)
        if self.running:
            c.start()
        self.connectors.append((overlay, connector))

    def removeOverlay(self, overlay):
        """
        Detach client from the specified overlay.  

        @param overlay: overlay controller
        @type  overlay: L{overlay.controller.Controller}
        """
        for possible, connector in self.connectors:
            if possible is overlay:
                break
        else:
            return
        if self.running:
            connector.stop()
        self.connectors.remove((overlay, connector))

    def start(self):
        """
        Start the client.
        """
        assert not self.running, "already running"
        def cb(whatever):
            for overlay, connector in self.connectors:
                connector.start()
        self.storage.check().addCallback(cb)
        self.choker.start()
        self.running = True
        
    def stop(self):
        """
        Stop the client.
        """
        assert self.running, "not running"
        for overlay, connector in self.connectors:
            connector.stop()
        self.choker.stop()
        self.running = False
