
from twisted.internet import protocol
from overlay import connection
from OpenSSL import SSL


class Factory(protocol.Factory):
    protocol = connection.Connection

    def __init__(self, controller, verifier):
        self.controller = controller
        self.verifier = verifier

    def buildProtocol(self, address):
        p = self.protocol(self.controller, self.verifier)
        p.factory = self
        return p


class ContextFactory:
    """
    @ivar cert:
    @type cert: L{PrivateCertificate}
    """

    def __init__(self, cert):
        self.cert = cert
        self._context = None

    def cacheContext(self):
        ctx = SSL.Context(SSL.TLSv1_METHOD)
        ctx.use_certificate(self.cert.original)	# XXX: should have a
        					# getter for this
        ctx.use_privatekey(self.cert.privateKey.original)
        verifyFlags = SSL.VERIFY_PEER
        verifyFlags |= SSL.VERIFY_FAIL_IF_NO_PEER_CERT
        def _trackVerificationProblems(conn,cert,errno,depth,preverify_ok):
            # retcode is the answer OpenSSL's default verifier would have
            # given, had we allowed it to run.
            #print "preverify", preverify_ok
            return 1 # preverify_ok
        ctx.set_verify(verifyFlags, _trackVerificationProblems)

        self._context = ctx

    def getContext(self):
        if not self._context:
            self.cacheContext()
        return self._context


class TerminateFactory:
    """
    Server factory.
    """

    def terminatesProbe(self, q):
        return False

OverlayFactory = TerminateFactory
