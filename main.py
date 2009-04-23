from twisted.internet._threadedselect import install
reactor = install()

import objc, Foundation, AppKit, os
from PyObjCTools import AppHelper

def loadFramework(frameworkName):
    base_path = os.path.join(os.path.dirname(os.getcwd()), 'Frameworks')
    bundle_path = os.path.abspath(
        os.path.join(base_path, '%s.framework' % frameworkName)
        )
    objc.loadBundle(frameworkName, globals(), bundle_path=bundle_path) 

#base_path = os.path.join(os.path.dirname(os.getcwd()), 'Frameworks')
#bundle_path = os.path.abspath(
#    os.path.join(base_path, 'BWToolkitFramework.framework')
#    )
#objc.loadBundle('BWToolkitFramework', globals(), bundle_path=bundle_path) 
loadFramework('BWToolkitFramework')
loadFramework('Automator')
    
# import modules containing classes required to start application and
# load MainMenu.nib:
from friendly import app, master, account, contacts

# pass control to AppKit
reactor.interleave(AppHelper.callAfter)
reactor.addSystemEventTrigger('after', 'shutdown', AppHelper.stopEventLoop)
AppHelper.runEventLoop()
