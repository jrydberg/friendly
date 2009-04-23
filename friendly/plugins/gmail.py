from twisted.names.srvconnect import SRVConnector
from twisted.words.protocols.jabber import xmlstream, client, jid
from zope.interface import implements
from twisted.plugin import IPlugin
from friendly.ifriendly import IContactImporter
from twisted.internet import defer, reactor
import sys


class XMPPClientConnector(SRVConnector):

    def __init__(self, reactor, domain, factory):
        SRVConnector.__init__(self, reactor, 'xmpp-client', domain, factory)

    def pickServer(self):
        host, port = SRVConnector.pickServer(self)

        if not self.servers and not self.orderedServers:
            # no SRV record, fall back..
            port = 5222

        return host, port


class GoogleTalkContactImporter(object):
    """
    """
    implements(IPlugin, IContactImporter)

    description = "Google Talk (gmail)"

    def connected(self, xs):
        self.status("Authenticating...")
        self.xmlstream = xs

    def disconnected(self, xs):
        self.factory.stopTrying()
        self.connector.disconnect()

    def rosterCallback(self, element):
        contacts = list()
        queryElement = element.firstChildElement()
        for itemElement in queryElement.elements():
            email = itemElement['jid']
            name = itemElement.getAttribute('name', email)
            contacts.append({
                    'name': name, 'email': email
                    })
        self.xmlstream.sendFooter()
        if self.deferred is not None:
            deferred, self.deferred = self.deferred, None
            deferred.callback(contacts)
            
    def authenticated(self, xs):
        """
        """
        self.status("Retreiving...")
        iq = client.IQ(xs, type="get")
        iq.addElement(("jabber:iq:roster", "query"))
        iq.addCallback(self.rosterCallback)
        iq.send()

    def initFailed(self, failure):
        if self.deferred is not None:
            deferred, self.deferred = self.deferred, None
            deferred.errback(failure)
        self.xmlstream.sendFooter()
    
    def importContacts(self, username, password, callback):
        """
        See L{IContactImporter.importContacts}.
        """
        self.status = callback
        self.deferred = defer.Deferred()
        self.jid = jid.JID(username)
        self.factory = client.XMPPClientFactory(self.jid, password)
        self.factory.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self.connected)
        self.factory.addBootstrap(xmlstream.STREAM_END_EVENT, self.disconnected)
        self.factory.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self.authenticated)
        self.factory.addBootstrap(xmlstream.INIT_FAILED_EVENT, self.initFailed)
        self.connector = XMPPClientConnector(reactor, self.jid.host, self.factory)
        self.connector.connect()
        return self.deferred
        

googleTalkContactImporter = GoogleTalkContactImporter()
