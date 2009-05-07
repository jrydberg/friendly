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
from AppKit import *
import random
from twisted.internet import ssl, reactor

from overlay.factory import Factory
from overlay.connector import Connector
from overlay.connection import Connection
from overlay.controller import OverlayController
from overlay.verifier import PublicFriendVerifier
from overlay.ssl import Connector as SSLConnector, Port, ClientCreator

from friendly.model import Account, Peer, Contact, selfSignedCertificate
from friendly.utils import initWithSuper, KeyValueBindingSupport, ContextFactory


class ContactVerifier:
    """
    Friend verifier that is based on Peer and Contact objects in the
    managed object context of the application.

    @ivar managedObjectContext: the context that holds Peer and
        Contact objects.
    @type managedObjectContext: L{NSManagedObjectContext}

    @ivar onlyContacts: C{true} if only contacts are allowed to contact
      us.
    @type onlyContacts: C{bool}
    """

    def __init__(self, managedObjectContext):
        """
        Initialize new contact friend verifier.
        """
        self.managedObjectContext = managedObjectContext
        self.onlyContacts = True

    def verifyFriend(self, certificate):
        """
        Verify that peer providing the given certificate may talk to
        us.

        @rtype: C{Deferred}
        """
        # create Friendly version of the certificate:
        certificate = Certificate.alloc().initWithNativeCertificate_(
            certificate.original
            )

        if self.onlyContacts:
            # If we only allow contacts to speak to us there must be
            # an existing Contact object in the database for the
            # certificate.
            peer = Contact.contactWithDigest_inManagedObjectContext_(
                certificate.digest(), self.managedObjectContext
                )
        else:
            peer = Peer.peerWithDigest_inManagedObjectContext(
                certificate.digest(), self.managedObjectContext
                )
            if peer is None:
                # create new peer: FIXME: assumes that alloc and
                # init... won't fail.
                peer = Peer.alloc()
                peer.initWithCertificate_insertIntoManagedObjectContext_(
                    certificate, self.managedObjectContext
                    )

        if peer is None:
            return defer.failure(None)

        return defer.succeed(peer)


class AccountController(NSObject):
    model = objc.ivar('model')

    bindingSupport = None
    listeningPort = None

    @initWithSuper
    def initWithApp_factory_model_(self, app, factory, model):
        """
        Initialize a new account controller with the given parameters.

        @param app: The application.
        @type  app: L{FriendlyAppController}
        @param factory: transfer factory
        @type  factory: L{OverlayFactory}
        @param model: account model
        @type  model: L{model.Account}
        """
        self.model = model

        # create verifier and context factory
        self.verifier = ContactVerifier(app.managedObjectContext())
        self.contextFactory = ContextFactory(model.certificate())

        # start the connectot that is responsible for connecting
        # this peer to other peers
        self.connector = Connector(self.connectionFactory)

        # create the swarm controller that is responsible for
        # connecting the overlay through this peer.
        self.controller = OverlayController('X', self.connector, factory)
        self.factory = Factory(self.controller, self.verifier)

        # setup bindings to the model
        self._bind('listenPort', model)

    def _bind(self, key, model):
        """
        Binding property to model to property of this controller.
        """
        self.bind_toObject_withKeyPath_options_(key, model, key, {})

    def bind_toObject_withKeyPath_options_(self, binding, anObject, keyPath, options):
        if self.bindingSupport is None:
            self.bindingSupport = KeyValueBindingSupport(self)
        self.bindingSupport.bind(binding, anObject, keyPath, options)

    def observeValueForKeyPath_ofObject_change_context_(self, keyPath, anObject,
                                                        change, context):
        self.bindingSupport.observe(keyPath, anObject, change)

    def connectionFactory(self, friend):
        """
        Connection factory.

        @rtype: L{Deferred}
        """
        c = ClientCreator(reactor, Connection, self.controller, self.verifier)
        factory = c.getFactory()
        c.connectWith(
            SSLConnector, friend.getHost().host, friend.getHost().port,
            factory, self.contextFactory, 30, None, reactor=reactor
            )
        return factory.deferred

    def setListenPort_(self, listenPort):
        """
        Set on what port the account listens for connections on.
        """
        if self.listeningPort is not None:
            self.listeningPort.stopListening()
        self.listeningPort = reactor.listenWith(
            Port, listenPort, self.factory, self.contextFactory,
            reactor=reactor
            )
        print "listening on port", listenPort

    def dealloc(self):
        print "stop controller"
        NSObject.dealloc(self)


class CreateAccountModel(NSObject):

    def init(self):
        self = NSObject.init(self)
        if self is None:
            return None
        self.onlyContacts = True
        self.announceList = []
        self.fullName = ""
        self.email = ""
        self.displayName = "New Account"
        self.listenPort = 1232
        self.usePortMapper = False
        self.useExistingIdentity = False
        return self


class CreateAccountController(NSWindowController):
    model = objc.IBOutlet()
    announceController = objc.IBOutlet()
    announceTable = objc.IBOutlet()

    def initWithApp_(self, app):
        """
        Initialize a new create-account dialog window controller.
        """
        self = NSWindowController.initWithWindowNibName_owner_(
            self, "CreateAccount", self)
        self.app = app
        return self
        
    def addAnnounceEntry_(self, sender):
        """
        """
        insertedObject = self.announceController.newObject()
        row = self.announceTable.numberOfRows()
        self.announceController.insertObject_atArrangedObjectIndex_(
            insertedObject, row
            )
        self.announceTable.editColumn_row_withEvent_select_(
            0, row, None, True
            )
        
    def randomizeListenPort_(self, sender):
        """
        Randomize listen port.
        """
        self.model.listenPort = random.randint(1024, 65535)

    def createAccount_(self, sender):
        """.
        """
        sslopt = dict()
        if self.model.fullName or self.model.email:
            if self.model.fullName and self.model.email:
                emailAddress = "%s <%s>" % (
                    self.model.fullName,
                    self.model.email
                    )
            elif self.model.fullName:
                emailAddress = self.model.fullName
            else:
                emailAddress = self.model.email
            sslopt['emailAddress'] = emailAddress
        serialNumber = 1
        cert = selfSignedCertificate(serialNumber, **sslopt)
        print 'SSL certificate generated:'
        print cert.inspect()

        # create the new account
        account = Account.alloc().initAndInsertIntoManagedObjectContext_(
            self.app.managedObjectContext()
            )
        account.setCertificate_(cert)
        account.setName_(self.model.displayName)
        account.setListenPort_(self.model.listenPort)
        self.app.startAccountController_(account)
        self.close()
        
    def openIdentityFile_(self, sender):
        pass
