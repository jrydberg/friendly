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

import objc

from OpenSSL import SSL, crypto


class ContextFactory:
    """
    @type cert: L{PrivateCertificate}
    """

    def __init__(self, cert):
        self.cert = cert
        self._context = None

    def cacheContext(self):
        ctx = SSL.Context(SSL.TLSv1_METHOD)
        ctx.use_certificate(self.cert.original) # XXX: should have a
                                                # getter for this
        ctx.use_privatekey(self.cert.privateKey.original)
        verifyFlags = SSL.VERIFY_PEER
        verifyFlags |= SSL.VERIFY_FAIL_IF_NO_PEER_CERT
        def _trackVerificationProblems(conn,cert,errno,depth,preverify_ok):
            # retcode is the answer OpenSSL's default verifier would have
            # given, had we allowed it to run.
            #print "preverify", preverify_ok
            return 1 # preverify_ok
        ctx.set_verify(verifyFlags, _trackVerificationProblems)

        self._context = ctx

    def getContext(self):
        if not self._context:
            self.cacheContext()
        return self._context


class KeyValueBindingSupport:
    """
    Class that helps the user to implement the
    NSKeyValueBindingCreation protocol.
    """

    def __init__(self, instance):
        self.bindings = {}
        self.instance = instance
        self.ignore = list()

    def bind(self, binding, toObject, keyPath, options, realize=True):
        """
        Establishes binding between the given property C{binding} and
        the property of the given object specified by C{keyPath}.

        @param realize: True if the binding should be realized now.
        """
        toObject.addObserver_forKeyPath_options_context_(self.instance, keyPath, 0, None)
        self.bindings[(toObject, keyPath)] = binding
        if realize:
            self.observe(keyPath, toObject, {})

    def unbind(self, binding):
        bindings = list()
        for (object, keypath), value in self.bindings.iteritems():
            if value == binding:
                bindings.append((object, keypath))
        for object, keypath in bindings:
            del self.bindings[(object, keypath)]

    def realize(self):
        """
        Realize all bindings.
        """
        for object, keypath in self.bindings:
            self.observe(keyPath, object, {})

    def observe(self, keyPath, object, change):
        if (object, keyPath) in self.ignore:
            return
        try:
            binding = self.bindings[(object, keyPath)]
        except IndexError:
            return
        self.ignore.append((object, keyPath))
        self.instance.setValue_forKey_(object.valueForKey_(keyPath), binding)
        self.ignore.remove((object, keyPath))


def selector(signature):
    def decorator(fn, signature=signature):
        return objc.selector(fn, signature=signature)
    return decorator


def initWithSuper(original):
    """
    Method decorator to simply writing init-method for PyObjC classes.
    
    This decorator eliminates the need to call [super init] and check
    the result of None.  Plus you do not have to remember to return
    'self', since that is already done for you.
    """
    def method(self, *args):
        initMethod = self.__class__.__bases__[0].init
        self = initMethod(self)
        if self is None:
            return None
        original(self, *args)
        return self
    return method

