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
from CoreData import *

from twisted.internet import reactor

from friendly.utils import selector, initWithSuper
from friendly.account import CreateAccountController
from friendly.contacts import (ImportContactsController,
                               ContactListController)

from os.path import expanduser
import objc, os


# FIXME: use a plist for these?  what's the upside?
standardDefaults = {
    'defaultDownloadLocation': expanduser("~/Downloads"),
    }


class CoreDataCoordinator:
    """
    Coordinator for everything that is related to Core Data.

    @ivar modelFile: Absolute path to where the data is stored.
    """
    _model = None
    _storeCoordinator = None
    _context = None

    def __init__(self, modelFile):
        self.modelFile = modelFile

    def model(self):
        """
        Return the Core Data NS{NSManagedObjectModel}.
        """
        if self._model is None:
            self._model = NSManagedObjectModel.mergedModelFromBundles_(None)
        return self._model

    def coordinator(self):
        """
        Return Core Data persistent store coordinator.
        """
        if self._storeCoordinator is None:
            url = NSURL.fileURLWithPath_(self.modelFile)
            self._storeCoordinator = NSPersistentStoreCoordinator.alloc()
            self._storeCoordinator.initWithManagedObjectModel_(self.model())
            success, error = self._storeCoordinator.addPersistentStoreWithType_configuration_URL_options_error_(
                NSXMLStoreType, None, url, None, None
                )
            assert success, "could not add persistent store"
        return self._storeCoordinator
        
    def context(self):
        """
        Return managed object context for this Core Data coordinator.
        """
        if self._context is None:
            self._context = NSManagedObjectContext.alloc().init()
            self._context.setPersistentStoreCoordinator_(self.coordinator())
        return self._context

    def save(self, commitEditing=False):
        if commitEditing:
            if not self.context().commitEditing():
                return False
        if self.context().hasChanges():
            success, error = self.context().save_(None)
            if not success:
                return False
        return True


class FriendlyAppController(NSObject):
    createAccountController = None
    importContactsController = None
    cachedAppSupportFolder = None
    contactListController = None
    
    @initWithSuper
    def init(self):
        # create the core data coordinator for our data:
        self._coreDataCoordinator = CoreDataCoordinator(
            os.path.join(self.applicationSupportFolder(), "Friendly.xml")
            )

    def applicationWillFinishLaunching_(self, sender):
        """
        """
        # register defaults before anything else
        defaultsController = NSUserDefaults.standardUserDefaults()
        defaultsController.registerDefaults_(standardDefaults)
        # try out the coordinator.
        context = self.managedObjectContext()
    
    def applicationDidFinishLaunching_(self, sender):
        """
        Degelate method that informs us that the application finished
        loading.
        """
        NSLog("Application did finish launching.")

    def applicationShouldTerminate_(self, sender):
        """
        Notification that the application is about to terminate.

        @return: Whether the application should terminate or not.
        """
        if not self._coreDataCoordinator.save(commitEditing=True):
            return NSTerminateCancel
        if reactor.running:
            reactor.stop()
            return False
        return NSTerminateNow

    # torrent/bundle handling:

    @objc.IBAction
    def openBundle_(self, sender):
        """
        Open bundle/torrent.
        """
        openPanel = NSOpenPanel.openPanel()
        window = NSApplication.sharedApplication().mainWindow()
        openPanel.beginSheetForDirectory_file_types_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
            "~/Downloads", None, ['torrent'], window,
            self, self.openPanelDidEnd_returnCode_contextInfo_, None
            )

    @selector("v@:@i^v")
    def openPanelDidEnd_returnCode_contextInfo_(self, sheet, returnCode,
                                                context):
        if returnCode:
            self.application_openFile_(self, sheet.filenames()[0])

    def openFile_withUI_(self, filename, withUI):
        """
        """
        defaultsController = NSUserDefaults.standardUserDefaults()
        location = defaultsController.stringForKey_(
            "defaultDownloadLocation"
            )
        print location
        return True
        
    def application_openTempFile_(self, sender, filename):
        if self.openFile_(filename, True):
            try:
                os.unlink(filename)
            except (IOError, OSError):
                return False
            return True
        return False
                
    def application_openFile_(self, sender, filename):
        """
        Delegate method: application:openFile:
        """
        return self.openFile_withUI_(filename, True)        

    def application_openFileWithoutUI_(self, sender, filename):
        """
        Delegate method: application:openFileWithoutUI:
        """
        return self.openFile_withUI_(filename, False)

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

    # core data:

    def managedObjectContext(self):
        """
        Core Data context accessor.

        @rtype: L{NSManagedObjectContext}
        """
        return self._coreDataCoordinator.context()

    def windowWillReturnUndoManager_(self, window):
        """
        Return undo manager.
        """
        return self.managedObjectContext().undoManager()
        
    @objc.IBAction
    def saveAction_(self, sender):
        self._coreDataCoordinator.save()

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
        

    def addAccount_(self, account):
        """
        Add account.
        """
        self.willChangeValueForKey_('accounts')
        self.accounts.addObject_(account)
        self.didChangeValueForKey_('account')
        self.saveAccounts()
        # tell everyone that contacts also changed
        self.willChangeValueForKey_('contacts')
        self.didChangeValueForKey_('contacts')

    @objc.accessor
    def contacts(self):
        """
        """
        contacts = list()
        if self.accounts:
            for account in self.accounts:
                contacts.extend(account.contacts)
        return contacts

    @objc.accessor
    def setContacts_(self, contacts):
        print "setContcts"
    
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

    @objc.IBAction
    def windowMain_(self, sender):
        """
        """
        w = NSApplication.sharedApplication().mainWindow()
        w.makeKeyAndOrderFront_(self)
        
    @objc.IBAction
    def windowContacts_(self, sender):
        """
        """
        if self.contactListController is None:
            self.contactListController = \
                ContactListController.alloc().initWithApp_(self)
        self.contactListController.window().makeKeyAndOrderFront_(self)
