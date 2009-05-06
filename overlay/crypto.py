from twisted.internet import ssl
from OpenSSL import crypto


class Certificate(ssl.Certificate):

    def __getstate__(self):
        return self.dump()

    def __setstate__(self, state):
        self.__init__(crypto.load_certificate(crypto.FILETYPE_ASN1, state))


class PrivateCertificate(ssl.PrivateCertificate):

    def __getstate__(self):
        return self.dump()

    def __getstate__(self, state):
        self.__init__(crypto.load_certificate(crypto.FILETYPE_ASN1, state))
