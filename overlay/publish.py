
from twisted.internet import task, reactor
from twisted.internet.ssl import Certificate
from twisted.python import log
from twisted.web import client
from overlay.friend import Friend, addressFactory
from base64 import b64decode, b64encode

# Remaining to do is to support re-setting the endpoint so that
# NAT-trav works.-


class Publisher(task.LoopingCall):
    """
    The publisher is responsible for connecting publishing our
    certificate and endpoint information and to retreive other
    endpoints that we can communicate with and supply them to the
    selector.

    @ivar cert: the certiticate that should be published
    @type cert: L{twisted.internet.ssl.Certificate}
    @ivar endpoint: the endpoint information that should be published
    @type endpoint: L{IEndpoint}
    @ivar contacts: the contact list that should be feed friends and
        endpoints
    @type contacts: L{IContacts}
    """

    def __init__(self, connector, cert, endpoint,
                 announce, contextFactory=None, clock=None):
        task.LoopingCall.__init__(self, self.publish)
        self.connector = connector
        self.cert = cert
        self.endpoint = endpoint
        self.announce = announce
        if clock is None:
            clock = reactor
        self.clock = clock
        self.contextFactory = contextFactory
        clock.callLater(0, self.start, 60, True)

    def _cbPublish(self, data):
        for line in data.splitlines():
            cdata, edata = line.strip().split(' ')
            ssc = Certificate.load(b64decode(cdata))
            print "got friend", ssc.digest(), "at", edata
            if ssc.digest() == self.cert.digest():
                print "got my own"
                continue	# got our own certificate
            friend = Friend(ssc)
            friend.setHost(addressFactory(edata))
            try:
                self.connector.addFriend(friend)
            except ValueError:
                print "got a duplicate friend"
        # done

    def publish(self):
        """
        Publish certificate and fetch friends.
        """
        # FIXME: instead of getHost+getPort use some other normalized
        # form
        body = '%s %s:%s\n' % (b64encode(self.cert.dump()),
                               self.endpoint.getHost().host,
                               self.endpoint.getHost().port)
        d = client.getPage(self.announce, self.contextFactory,
                           method='POST', postdata=body,
                           agent='overlay-client', timeout=20)
        return d.addCallback(self._cbPublish).addErrback(log.deferr)

