#
#
#

from Foundation import *
from OpenSSL import crypto
from twisted.internet.ssl import Certificate


class Contact(NSObject):
    """
    """
    name = objc.ivar('name')
    email = objc.ivar('email')
    cert = objc.ivar('cert')
    status = objc.ivar('status')
    account = objc.ivar('account')
    endpont = objc.ivar('endpoint')
    
    def initWithName_andEmail_(self, name, email):
        self = NSObject.init(self)
        if self is None:
            return None
        self.name = name
        self.email = email
        self.cert = None
        self.status = 1
        self.account = None
        return self

    def initWithCoder_(self, coder):
        """
        Initialize model object with the content from the L{NSCoder}.
        """
        self = NSObject.init(self)
        if self is None:
            return None
        self.account = None
        self.cert = None
        self.name = coder.decodeObjectForKey_("name")
        self.email = coder.decodeObjectForKey_("email")
        certBytes, lenBytes = coder.decodeBytesForKey_returnedLength_(
            "cert", None
            )
        print lenBytes
        if lenBytes:
            self.cert = Certificate.load(certBytes)
        return self

    def encodeWithCoder_(self, coder):
        """
        Encode instance with L{NSCoder} provided in coder.
        """
        coder.encodeObject_forKey_(self.name, "name")
        coder.encodeObject_forKey_(self.email, "email")
        if self.cert is not None:
            certBytes = self.cert.dump()
        else:
            certBytes = ''
        coder.encodeBytes_length_forKey_(certBytes, "cert")
        #coder.encodeBytes_length_forKey_(certBytes, len(certBytes), "cert")

    def setCertificate_(self, cert):
        """
        Set certificate of peer.
        """
        self.cert = cert


class Account(NSObject):
    displayName = objc.ivar('displayName')
    contacts = objc.ivar('contacts')
    cert = objc.ivar('cert')
    
    def init(self):
        self = NSObject.init(self)
        if self is None:
            return None
        self.displayName = u""
        self.contacts = NSMutableArray.alloc().initWithCapacity_(0)
        self.cert = None
        return self

    def initWithName_andCert_(self, name, cert):
        """
        """
        self = self.init()
        if self is None:
            return None
        self.displayName = name
        self.cert = cert
        return self
        
    def initWithCoder_(self, coder):
        """
        Initialize account model object with the content from the
        L{NSCoder}.
        """
        self = NSObject.init(self)
        if self is None:
            return None
        self.displayName = coder.decodeObjectForKey_("displayName")    
        self.contacts = coder.decodeObjectForKey_("contacts")
        if self.contacts is None:
            self.contacts = NSMutableArray.alloc().initWithCapacity_(0)
        return self
        
    def encodeWithCoder_(self, coder):
        """
        Encode account with encoder.
        """
        coder.encodeObject_forKey_(self.displayName, "displayName")
        coder.encodeObject_forKey_(self.contacts, "contacts")
        
    def addContact_(self, contact):
        """
        Add contact to list of contacts.
        """
        self.willChangeValueForKey_('contacts')
        self.contacts.addObject_(contact)
        self.didChangeValueForKey_('contacts')

    def removeContact_(self, contact):
        """
        Remove contact from list of contacts.
        """
        self.willChangeValueForKey_('contacts')
        self.contacts.removeObject_(contact)
        self.didChangeValueForKey_('contacts')
        
    def hasContactWithEmail_(self, email):
        """
        Return C{True} if the account has a contact with the given
        email.
        """
        for contact in self.contacts:
            if contact.email == email:
                return True
        return False
    
