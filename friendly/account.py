from Foundation import *
from AppKit import *
import random
from twisted.internet import ssl
from friendly.model import Account


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
