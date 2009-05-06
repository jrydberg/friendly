from twisted.internet.interfaces import IAddress
from zope.interface import implements
from overlay.utils import short_hash


class OverlayAddress(object):
    """"
    Object representing a overlay path endpoint.

    @ivar pid: the path identifier
    @ivar cid: the channel identifier
    @ivar friend:
    """

    def __init__(self, q, pid, cid, friend):
        self.q = q
        self.pid = pid
        self.cid = cid
        self.friend = friend

    def __str__(self):
        """
        Return a string that describes this address.
        """
        return "OverlayAddress(Q=%s, PID=%s, CID=%s>" % (
            short_hash(self.q), short_hash(self.pid), short_hash(self.cid)
            )
