from twisted.internet import task, reactor

import random

try:
    from twisted.python.randbytes import insecureRandom
except ImportError:
    insecureRandom = None


def randbytes(n):
    if insecureRandom is not None:
        return insecureRandom(n)
    return ''.join([chr(random.randrange(256)) for n in xrange(n)])


def short_hash(d):
    s = ':'.join([('%02x' % ord(v)) for v in d])
    return s[:5] + '...' + s[-5:]

# FIXME: patch reactor to have seconds


class LoopingCall(task.LoopingCall):
    """
    Subcall of task.LoopingCall that easier supports using Clock.

    """

    def _callLater(self, delay):
        self.clock.callLater(delay, self)

    def _seconds(self):
        return self.clock.seconds()

    def __init__(self, clock, f, *args, **kw):
        task.LoopingCall.__init__(self, f, *args, **kw)
        if clock is None:
            clock = reactor
        self.clock = clock

