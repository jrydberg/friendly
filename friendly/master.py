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

from MGScopeBar import (MGRadioSelectionMode,
                        MGMultipleSelectionMode)


class MasterListController(NSObject):
    accessoryView = objc.IBOutlet()
    scopeBar = objc.IBOutlet()
    
    @objc.IBAction
    def filter_(self, sender):
        print "GOT FILTER", self.appDelegate

    def awakeFromNib(self):
        self.scopeBar.reloadData()
        
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

    # MGScopeBarDataSource:

    def accessoryViewForScopeBar_(self, view):
        print "GET ACCESSORY", self.accessoryView
        return self.accessoryView
    
    def numberOfGroupsInScopeBar_(self, view):
        """
        Return the number of groups in the scope bar.
        """
        return 2

    def scopeBar_itemIdentifiersForGroup_(self, view, groupIndex):
        """
        Return item identifiers for the specified group.
        """
        if groupIndex == 0:
            return ["all", "mine"]
        elif groupIndex == 1:
            return ["all", "downloading", "completed", "inactive"]
    
    def scopeBar_labelForGroup_(self, view, groupIndex):
        """
        Return label for the group.  
        """
        if groupIndex == 0:
            return "Whos:"
        elif groupIndex == 1:
            return "Kind:"
    
    def scopeBar_selectionModeForGroup_(self, view, groupIndex):
        """
        Return selection mode for group.
        """
        return MGRadioSelectionMode

    def scopeBar_titleOfItem_inGroup_(self, view, identifier, groupIndex):
        """
        Return title of item.
        """
        if groupIndex == 0:
            if identifier == 'all':
                return "All"
            elif identifier == 'mine':
                return "Mine"
        elif groupIndex == 1:
            if identifier == 'all':
                return "All"
            elif identifier == "downloading":
                return "Downloading"
            elif identifier == "completed":
                return "Completed"
            elif identifier == "inactive":
                return "Inactive"

    def scopeBar_showSeparatorBeforeGroup_(self, view, groupIndex):
        """
        Return whether a separator should be rendered before given group.
        """
        return (groupIndex != 0)

    def scopeBar_imageForItem_inGroup_(self, view, identifier, groupIndex):
        """
        Return possible C{NSImage} to display before item.
        
        @rtype: a NSImage.
        """
        if groupIndex == 0:
            if identifier == 'all':
                return NSImage.imageNamed_("NSNetwork")
            elif identifier == 'mine':
                return NSImage.imageNamed_("NSComputer")
        elif groupIndex == 2:
            #if identifier == "AllFilesItem":
            #    return NSImage.imageNamed_("NSGenericDocument")
            #else:
            #    return NSWorkspace.sharedWorkspace().iconForFileType_("png")
            pass
        return None

    # MGScopeBarDelegate:

    def scopeBar_selectedStateChanged_forItem_inGroup_(self, view, selected, 
                                                       identifier, groupIndex):
        """
        Delegate method that is invoked when state is changed for an
        item.
        """
        displayString = "'%s' %s in group %d." % (
            self.scopeBar_titleOfItem_inGroup_(view, identifier, groupIndex),
            (selected and "selected" or "deseelcted"),
            groupIndex
            )
        #self.label.setStringValue_(displayString)
