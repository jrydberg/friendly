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
from twisted.internet import ssl

from friendly.model import Account
from friendly.utils import initWithSuper


class AccountController(NSObject):
    bindingSupport = None

    @initWithSuper
    def initWithAccountModel_(self, model):
        self.model = model
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
        cert = ssl.KeyPair.generate().selfSignedCert(serialNumber,
                                                     **sslopt)
        print 'SSL certificate generated:'
        print cert.inspect()

        # create the new account
        account = Account.alloc().initWithName_andCert_(
            self.model.displayName, cert
            )
        self.app.addAccount_(account)
        self.close()
        
    def openIdentityFile_(self, sender):
        pass
