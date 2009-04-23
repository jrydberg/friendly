#
#  FriendlyAppDelegate.py
#  Friendly
#
#  Created by Johan Rydberg on 4/13/09.
#  Copyright __MyCompanyName__ 2009. All rights reserved.
#
from twisted.internet import reactor

from Foundation import *
from AppKit import *
import objc

class MasterListController(NSObject):
    outlineTable = objc.IBOutlet()
    filterMatrix = objc.IBOutlet()
    searchTextfield = objc.IBOutlet()
    appDelegate = objc.IBOutlet()
    
    @objc.IBAction
    def filter_(self, sender):
        print "GOT FILTER", self.appDelegate

    def outlineView_numberOfChildrenOfItem_(self, outline, item):
        if item is None:
            return 1
        else:
            return 0

    def outlineView_isItemExpandable_(self, outline, item):
        return False

    def outlineView_child_ofItem_(self, outline, index, item):
        return None
        #if item == None:
        #    return "ROOT"
        #else:
        #    return "CHILD %d" % index

    def outlineView_objectValueForTableColumn_byItem_(self, outline,
                                                      tableColumn,
                                                      item):
        col = tableColumn.identifier()
        if col == 'rating':
            return 3
        elif col == 'done':
            return 50
        elif col == 'size':
            return 1.2*1024*1024
        print col, tableColumn
        return "XXX"

    def outlineView_setObjectValue_forTableColumn_byItem_(self, outline,
                                                          value,
                                                          tableColumn,
                                                          item):
        col = tableColumn.identifier()
        print "set", col, value


    def outlineViewSelectionDidChange_(self, notification):
        print "selected", self.outlineTable.selectedRow()
