from overlay.protocols.bt.connection import Connection


class ClientFactory:
    """
    Factory or building Connection protocol instances for a client.

    @ivar controller: L{overlay.protocols.bt.controller.Controller}
    """
    
    def __init__(self, controller, metainfo):
        self.controller = controller
        self.metainfo = metainfo
    
    def buildProtocol(self, address):
        if address.q != self.metainfo.rootHash:
            return None
        return Connection(self.controller, self.metainfo)
