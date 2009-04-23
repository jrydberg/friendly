from twisted.internet import reactor

from Foundation import *
from AppKit import *
import objc, os

from friendly.account import CreateAccountController
from friendly.contacts import ImportContactsController


class FriendlyAppController(NSObject):
    showContacts = objc.ivar('showContacts')

    createAccountController = None
    importContactsController = None
    cachedAppSupportFolder = None
    
    def init(self):
        self = NSObject.init(self)
        if self is not None:
            self.showContacts = True
        self.accounts = None
        return self

    def applicationSupportFolder(self):
        """
        Return directory where application specific data will be
        stored.
        """
        if self.cachedAppSupportFolder is None:
            paths = NSSearchPathForDirectoriesInDomains(
                NSApplicationSupportDirectory, NSUserDomainMask, True
                )
            basePath = paths[0] if (len(paths) > 0) else NSTemporaryDirectory()
            self.cachedAppSupportFolder = os.path.join(basePath, "Friendly")
            if not os.path.exists(self.cachedAppSupportFolder):
                try:
                    os.makedirs(self.cachedAppSupportFolder)
                except OSError:
                    pass
        return self.cachedAppSupportFolder

    def applicationDidFinishLaunching_(self, sender):
        """
        Degelate method that informs us that the application finished
        loading.
        """
        # load accounts:
        self.accounts = NSKeyedUnarchiver.unarchiveObjectWithFile_(
            os.path.join(self.applicationSupportFolder(), 'accounts.keyarch')
            )
        if self.accounts is None:
            print "no accounts"
            self.accounts = NSMutableArray.alloc().initWithCapacity_(0)
        print self.accounts
            
        NSLog("Application did finish launching.")

    def saveAccounts(self):
        """
        Save accounts to the persistent store.
        """
        print "save accounts"
        x = NSKeyedArchiver.archiveRootObject_toFile_(
            self.accounts,
            os.path.join(self.applicationSupportFolder(), 'accounts.keyarch')
            )
        print "x is ", x
        print self.accounts
        
    def applicationShouldTerminate_(self, sender):
        if reactor.running:
            reactor.stop()
            return False
        return True

    def addAccount_(self, account):
        """
        Add account.
        """
        self.willChangeValueForKey_('accounts')
        self.accounts.addObject_(account)
        self.didChangeValueForKey_('account')
        self.saveAccounts()
        
    @objc.IBAction
    def createAccount_(self, sender):
        """
        """
        if self.createAccountController is None:
            self.createAccountController = \
                CreateAccountController.alloc().initWithApp_(self)
        self.createAccountController.window().makeKeyAndOrderFront_(self)

    @objc.IBAction
    def importContacts_(self, sender):
        if self.importContactsController is None:
            self.importContactsController = \
                ImportContactsController.alloc().initWithApp_(self)
        self.importContactsController.window().makeKeyAndOrderFront_(self)
