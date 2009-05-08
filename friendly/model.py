# This file is part of Friendly.
# Copyright (c) 2009 Johan Rydberg <johan.rydberg@gmail.com>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

from Foundation import *
from CoreData import (NSManagedObject, NSFetchRequest, 
                      NSEntityDescription)
from OpenSSL import crypto

from twisted.internet import ssl

from friendly.utils import initWithSuper


def selfSignedCertificate(serialNumber, **kw):
    """
    Create a self signed certificate.

    @rtype: L{PrivateCertificate}
    """
    kp = ssl.KeyPair.generate()
    dn = ssl.DN(**kw)
    return PrivateCertificate.fromCertificateAndKeyPair(
        kp.signRequestObject(dn, kp.requestObject(dn), serialNumber), kp
        )


class Certificate(NSObject, ssl.Certificate):
    """
    An x509 certificate that can be serialized using a keyed archiver.
    """

    @initWithSuper
    def initWithNativeCertificate_(self, original):
        ssl.Certificate.__init__(self, original)
    
    def initWithCoder_(self, coder):
        """
        Returns an object initialized from data in a given unarchiver.

        @param coder: they keyed unarchiver
        @rtype: a L{Certificate} instance
        """
        self = NSObject.init(self)
        if self is None:
            return None
        data, l = coder.decodeBytesForKey_returnedLength_("certificate", None)
        self.__init__(crypto.load_certificate(crypto.FILETYPE_ASN1, d))
        return self

    def encodeWithCoder_(self, coder):
        """
        Encodes the receiver using a given archiver.

        @param coder: the keyed archiver.
        """
        coder.encodeBytes_length_forKey_(self.dump(), "certificate")


class PrivateCertificate(NSObject, ssl.PrivateCertificate):
    """
    An x509 certificate and private key that can be serialized using a
    keyed archiver.
    """

    @initWithSuper
    def initWithNativeCertificate_(self, original):
        ssl.PrivateCertificate.__init__(self, original)
    
    def initWithCoder_(self, coder):
        """
        Returns an object initialized from data in a given unarchiver.

        @param coder: they keyed unarchiver
        @rtype: a L{PrivateCertificate} instance
        """
        self = NSObject.init(self)
        if self is None:
            return None
        data, l = coder.decodeBytesForKey_returnedLength_("certificate", None)
        ssl.PrivateCertificate.__init__(
            self, crypto.load_certificate(crypto.FILETYPE_ASN1, data)
            )
        data, l = coder.decodeBytesForKey_returnedLength_("privateKey", None)
        return self._setPrivateKey(ssl.KeyPair.load(data))

    def encodeWithCoder_(self, coder):
        """
        Encodes the receiver using a given archiver.

        @param coder: the keyed archiver.
        """
        coder.encodeBytes_length_forKey_(self.dump(), "certificate")
        coder.encodeBytes_length_forKey_(self.privateKey.dump(), "privateKey")

    @classmethod 
    def fromCertificateAndKeyPair(Class, certificateInstance, privateKey):
        self = Class.alloc().initWithNativeCertificate_(certificateInstance.original)
        if self is None:
            return None
        return self._setPrivateKey(privateKey)


class Peer(NSManagedObject):
    """
    Model class for peers.

    @property certificate: The unique identifying certificate of the peer
    @type certificate: L{Certificate}

    @property digest: digest of certificate, indexed.
    @type digest: C{str}
    """

    def initWithCertificate_insertIntoManagedObjectContext_(self, certificate,
                                                            context):
        """
        Initialize new peer with given parameters and insert it into the
        specified managed object context.
        
        @type certificate: L{Certificate}
        """
        self = NSManagedObject.initWithEntity_insertIntoManagedObjectContext_(
            self, entityFromContext("Peer", context), context
            )
        if self is None:
            return None
        self.setCertificate_(certificate)
        return self

    @staticmethod
    def peerWithDigest_inManagedObjectContext_(digest, context):
        """
        Return peer that match given digest.
        """
        entity = NSEntityDescription.entityForName_inManagedObjectContext_("Peer", context)
        request = NSFetchRequest.alloc().init()
        request.setEntity_(entity)
        request.setPredicate_(NSPredicate.predicateWithFormat_("digest = %@", digest))
        peers, error = context.executeFetchRequest_error_(request, None)
        if not peers or error is not None:
            return None
        return peers[0]

    def touch(self):
        """
        Register that the peer has been seen.
        """
        self.setLastSeen_(NSDate.date())

    def setCertificate_(self, certificate):
        """
        Set certificate for peer.
        """
        self.setPrimitiveCertificate_(certificate)
        self.setDigest_(certificate.digest())

    def registerBytesReceived_(self, bytes):
        """
        Return that an amount of bytes has been read.
        """
        self.setReceivedBytes_(self.receivedBytes() + bytes)

    def registerBytesWritten_(self, bytes):
        """
        Register that an amount of bytes has been written.
        """
        self.setSentBytes_(self.sentBytes() + bytes)
    

class Contact(Peer):
    """
    An known contact.

    Contacts are just like any other peer, except that they have a
    known identity and that the certificate and endpoint information
    is gathered through a randevu service.

    @property name: Display name of the context
    @type name: C{str}

    @property email: E-mail address of contact, used as identity.
    @type email: C{str}
    """

    def initWithCertificate_insertIntoManagedObjectContext_(self, certificate,
                                                            context):
        """
        Initialize new contact with given parameters and insert it into the
        specified managed object context.
        
        @type certificate: L{PrivateCertificate}
        """
        self = NSManagedObject.initWithEntity_insertIntoManagedObjectContext_(
            self, entityFromContext("Contact", context), context
            )
        if self is None:
            return None
        self.setCertificate_(certificate)
        return self

    @staticmethod
    def newWithName_email_inManagedObjectContext_(name, email,
                                                  managedObjectContext):
        contact = NSEntityDescription.insertNewObjectForEntityForName_inManagedObjectContext_(
            "Contact", managedObjectContext
            )
        if contact is None:
            return None
        contact.setName_(name)
        contact.setEmail_(email)
        return contact

    @staticmethod
    def contactWithDigest_inManagedObjectContext_(digest, context):
        """
        Return peer that match given digest.
        """
        entity = NSEntityDescription.entityForName_inManagedObjectContext_(
            "Contact", context
            )
        request = NSFetchRequest.alloc().init()
        request.setEntity_(entity)
        request.setPredicate_(NSPredicate.predicateWithFormat_("digest = %@", digest))
        contacts, error = context.executeFetchRequest_error_(request, None)
        if not contacts or error is not None:
            return None
        return contacts[0]



def entityFromContext(entityName, context):
    return NSEntityDescription.entityForName_inManagedObjectContext_(
        entityName, context)


class Account(NSManagedObject):
    """
    Model object for Account settings.
    """

    @staticmethod
    def allAccountsInManagedObjectContext_(context):
        """
        Return a sequence of all Account objects in the managed object
        context.
        """
        r = NSFetchRequest.alloc().init()
        r.setEntity_(entityFromContext("Account", context))
        objects, error = context.executeFetchRequest_error_(r, None)
        return objects

    def initAndInsertIntoManagedObjectContext_(self, context):
        """
        Initialize new account and given parameters and insert it into
        the specified context.
        """
        return NSManagedObject.initWithEntity_insertIntoManagedObjectContext_(
            self, entityFromContext("Account", context), context
            )
