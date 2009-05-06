from twisted.internet import address


class IEndpoint:

    def getHost():
        """
        @rtype: L{IAddress}
        """


class Endpoint:
    #implements(IEndpoint):

    def __init__(self, address=None):
        self.address = address

    def getHost(self):
        return self.address

    def setHost(self, address):
        self.address = address


def addressFactory(s):
    """
    Factory for building L{IAddress} instances from a string
    """
    if s[0] == '[':
        # assume IPv6
        assert False, "ipv6 not supported"
    host, port = s.split(':')
    return address.IPv4Address('TCP', host, int(port))

        
class Friend:
    """
    Representatin of a friend, someone we can communicate with.

    @ivar cert: the certificate of the friend
    @type cert: L{twisted.internet.ssl.Certificate}
    """
    #implements(IEndpoint)

    def __init__(self, cert):
        self.cert = cert
        self.address = None

    def getCertificate(self):
        """
        Return certificate of the user.
        """
        return self.cert

    def getDisplayName(self):
        """
        Return display name of the user.
        """
        dn = self.cert.getSubject()['emailAddress']
        if not dn:
            dn = self.getIdentity()
        return dn

    def getIdentity(self):
        """
        Return a hashable unique identity of the friend.
        """
        return self.cert.digest()

    def __str__(self):
        i = self.getIdentity()
        return "%s..%s" % (i[:5], i[-5:])
    
    def __hash__(self):
        """
        Return a hash for this friend.
        """
        return hash(self.getIdentity())

    def __repr__(self):
        return "<Friend: %s>" % self.getIdentity()

    def __eq__(self, other):
        return other.getIdentity() == self.getIdentity()

    def getHost(self):
        return self.address

    def setHost(self, address):
        self.address = address
