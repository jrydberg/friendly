from Foundation import *
from AppKit import *
import random

from zope.interface import Interface
from twisted.plugin import getPlugins
from friendly import plugins, ifriendly
from friendly.model import Contact


class ImportContactsController(NSWindowController):
    """
    Coordinating controller for importing contacts.

    The controller is responsible for a window where the user may add
    display names and email addresses of contacts.
    """
    accountBox = objc.ivar('accountBox')
    contactTable = objc.ivar('contactTable')
    disclosureTriangle = objc.ivar('disclosureTriangle')
    passwordInput = objc.ivar('passwordInput')
    usernameInput = objc.ivar('usernameInput')
    serviceBox = objc.ivar('serviceBox')
    spinner = objc.ivar('spinner')
    statusLabel = objc.ivar('statusLabel')
    arrayController = objc.ivar('arrayController')
    accountController = objc.ivar('accountController')
    
    def initWithApp_(self, app):
        """
        Initialize new controller instance.
        """
        self = NSWindowController.initWithWindowNibName_owner_(
            self, "ImportContacts", self
            )
        if self is not None:
            self.app = app
        return self

    def awakeFromNib(self):
        self.disclosureTriangle.setState_(NSOffState)
        self.disclosurePressed_(self.disclosureTriangle)
        # get all contact importers.
        self.importers = list(
            getPlugins(ifriendly.IContactImporter, plugins)
            )
        self.serviceBox.removeAllItems()
        for importer in self.importers:
            self.serviceBox.addItemWithTitle_(importer.description)
        
    @objc.IBAction
    def addContacts_(self, sender):
        """
        """
        account = self.accountController.selectedObjects()[0]
        for description in self.arrayController.arrangedObjects():
            if not description['import']:
                continue
            name = description['name']
            email = description['email']
            if account.hasContactWithEmail_(email) or not len(email):
                continue
            contact = Contact.alloc().initWithName_andEmail_(
                name, email
                )
            account.addContact_(contact)
        self.app.saveAccounts()

    def _addContact(self, description):
        """
        Add a single description to the contact list.

        @param description: C{dict} describing the contact.
        """
        insertedObject = self.arrayController.newObject()
        insertedObject['import'] = True
        insertedObject['name'] = description['name']
        insertedObject['email'] = description['email']
        row = self.contactTable.numberOfRows()
        self.arrayController.insertObject_atArrangedObjectIndex_(
            insertedObject, row
            )
    
    def cbImporter(self, contacts):
        self.spinner.stopAnimation_(self)
        for contact in contacts:
            self._addContact(contact)
        self.status("Imported %d contacts" % len(contacts))

    def ebImporter(self, failure):
        self.status("Failed to import")
        print failure
        self.spinner.stopAnimation_(self)

    def status(self, message):
        self.statusLabel.setHidden_(False)
        self.statusLabel.setStringValue_(message)
        
    @objc.IBAction
    def addContactsFromService_(self, sender):
        importerIndex = self.serviceBox.indexOfSelectedItem()
        importer = self.importers[importerIndex]
        username = self.usernameInput.stringValue()
        password = self.passwordInput.stringValue()
        self.spinner.startAnimation_(self)
        d = importer.importContacts(username, password, self.status)
        d.addCallback(self.cbImporter)
        d.addErrback(self.ebImporter)

    @objc.IBAction
    def addNewContact_(self, sender):
        """
        """
        insertedObject = self.arrayController.newObject()
        insertedObject['import'] = True
        row = self.contactTable.numberOfRows()
        self.arrayController.insertObject_atArrangedObjectIndex_(
            insertedObject, row
            )
        self.contactTable.editColumn_row_withEvent_select_(
            1, row, None, True
            )

    @objc.IBAction
    def disclosurePressed_(self, sender):
        """
        Called when disclosure triangle has been pressed.
        """
        LARGE = 481 + 20
        SMALL = 285 + 20
        frame = self.window().frame()
        if sender.state() == NSOnState:
            frame.size.height = LARGE
            frame.origin.y -= (LARGE - SMALL)
        else:
            frame.size.height = SMALL
            frame.origin.y += (LARGE - SMALL)
        self.window().setFrame_display_animate_(frame, True, True)


class EndpointStringValueTransformer(NSValueTransformer):

    def transformedValueClass(self):
        return NSString

    def transformedValue_(self, endpoint):
        if endpoint is not None:
            return "XXX"
        return None


class CertificateFingerprintValueTransformer(NSValueTransformer):

    def transformedValueClass(self):
        return NSString

    def transformedValue_(self, cert):
        if cert is not None:
            return cert.digest()
        return None

            
class ContactStatusImageValueTransformer(NSValueTransformer):

    def init(self):
        self = NSValueTransformer.init(self)
        self.connectedImage = None
        return self
        
    def transformedValueClass(self):
        return NSImage

    def transformedValue_(self, value):
        if self.connectedImage is None:
            self.connectedImage = NSImage.imageNamed_(
                'status-connected'
                )
        return self.connectedImage
        

        
class ContactListController(NSWindowController):
    app = objc.IBOutlet()
    arrayController = objc.IBOutlet()

    def initWithApp_(self, app):
        self = NSWindowController.initWithWindowNibName_owner_(
            self, "ContactList", self)
        self.app = app
        return self

    @objc.IBAction
    def export_(self, sender):
        pass

    @objc.IBAction
    def connect_(self, sender):
        pass
