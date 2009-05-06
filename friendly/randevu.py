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

from twisted.internet import task
from twisted.web import client

from twisted.internet import task, reactor
from twisted.internet.ssl import Certificate
from twisted.python import log
from twisted.web import client
from base64 import b64decode, b64encode


class IRandevuDataSource:
    """
    Data source informal protocol.
    """

    def contacts():
        """
        Return a list of of contacts.
        """

    def endpoint():
        """
        Return a dictionary describing the endpoint.
        """

    def certificate():
        """
        Return certificate of this user.
        """


class Randevu(task.LoopingCall):
    """
    Process responsible for gathering certificates and endpoint
    information about contacts.

    @ivar dataSource: source for data.
    """

    def __init__(self, announce, dataSource, contextFactory):
        task.LoopingCall.__init__(self, self.publish)
        self.announce = announce
        self.dataSource = dataSource
        self.contactFactory = contextFactory

    def _cbPublish(self, data):
        """
        Callback with data from the randevu server.
        """
        result = {}

        for line in data.splitlines():
            try:
                email, certBytes, endpointBytes = line.strip().split(' ')
            except ValueError:
                continue

            endpointDict = {}
            for l in endpointBytes.split(','):
                try:
                    k, v = l.split('=')
                except ValueError:
                    continue
                endpointDict[k] = v

            # create new certificate:
            try:
                certificate = Certificate.alloc().initWithContent_(
                    b64decode(certBytes)
                    )
            except ValueError:
                continue	# bad certificate

            result[email] = (certificate, endpointDict)
        
        # update contacts:
        for contact in self.dataSource.contacts():

            try:
                certificate, endpoint = result[contact.email()]
            except KeyError:
                continue	# no information for contact

            contact.setCertificate_(certificate)
            contact.setEndpoint_(endpoint)

        # done

    def publish(self):
        lines = list()
        lines.append('%s %s %s' % (
                self.dataSource.name(),
                b64encode(self.dataSource.certificate.dump()),
                ','.join(
                    ['%s=%s' % (k, str(v)) for k, v in self.dataSource.endpoint().iteritems()]
                    )
                ))

        for contact in self.dataSource.contacts():
            lines.append(contact.email())

        d = client.getPage(self.announce, self.contextFactory,
                           method='POST', postdata='\n'.join(lines),
                           agent='Friendly-client', timeout=30)
        return d.addCallback(self._cbPublish).addErrback(log.deferr)

