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
from CoreData import *
from overlay import error
from friendly import account, app, model
from friendly.model import Peer, Contact, selfSignedCertificate
from twisted.python import util
from twisted.trial import unittest
import os


class CoreDataCoordinator(app.CoreDataCoordinator):

    def model(self):
        if self._model is None:
            path = os.path.join(
                util.sibpath(app.__file__, "resources"), "DataModel.mom"
                )
            self._model = NSManagedObjectModel.alloc().initWithContentsOfURL_(
                NSURL.fileURLWithPath_(path)
                )
        return self._model


class _BaseVerifierTestCase(unittest.TestCase):
    """
    Base class for verifier test cases.
    """

    def setUp(self):
        self.coordinator = CoreDataCoordinator("verifier.xml")
        self.verifier = account.ContactVerifier(self.coordinator.context())

        # add a simple contacts:
        self.contact1cert = selfSignedCertificate(1)
        self.contact1 = Contact.alloc().initWithCertificate_insertIntoManagedObjectContext_(
            self.contact1cert, self.coordinator.context()
            )

        self.contact2cert = selfSignedCertificate(1)
        self.contact2 = Contact.alloc().initWithCertificate_insertIntoManagedObjectContext_(
            self.contact2cert, self.coordinator.context()
            )

        # add a simple peer:
        self.peer1cert = selfSignedCertificate(1)
        self.peer1 = Peer.alloc().initWithCertificate_insertIntoManagedObjectContext_(
            self.peer1cert, self.coordinator.context()
            )


class OnlyContactsVerifierTestCase(_BaseVerifierTestCase):

    def setUp(self):
        _BaseVerifierTestCase.setUp(self)
        self.verifier.onlyContacts = True

    def test_disallowKnownPeer(self):
        """
        Verify that the verifier can identify and only allow contacts.
        """
        def cb(friend):
            self.assertTrue(False)
        def eb(reason):
            reason.trap(error.NotAllowedPeerError)
        return self.verifier.verifyFriend(self.peer1cert).addCallback(cb).addErrback(eb)

    def test_allowKnownContact(self):
        """
        Verifyt that a known contact is accepted.
        """
        def cb(friend):
            self.assertTrue(friend is self.contact1)
        return self.verifier.verifyFriend(self.contact1cert).addCallback(cb)


class NotOnlyContactsVerifierTestCase(_BaseVerifierTestCase):

    def setUp(self):
        _BaseVerifierTestCase.setUp(self)
        self.verifier.onlyContacts = False

    def test_newContact(self):
        """
        Verify that new Peer's are created.
        """
        certificate = selfSignedCertificate(1)
        def cb(friend):
            self.assertEquals(friend.certificate().digest(),
                              certificate.digest())
        return self.verifier.verifyFriend(certificate).addCallback(cb)

    def test_knownContactAsPeer(self):
        """
        Verifyt that a known contact is accepted.
        """
        def cb(friend):
            self.assertTrue(friend is self.contact1)
        return self.verifier.verifyFriend(self.contact1cert).addCallback(cb)
