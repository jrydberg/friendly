from twisted.python import log
from twisted.internet import reactor, task


class TickCall(task.LoopingCall):
    """
    The L{TickCall} provides means to let functions be called with
    regular intervals, where the interval is a multiple of the base
    interval.
    
    Two functions that are supposed to be called at the same 'tick'
    is guraranteed to be so.

    For example, to have L{foo} be called every 10th second, and
    L{bar} be called every 20th second:

      >>> t = TickCall(10)
      >>> t.add(1, foo)
      >>> t.add(2, bar)

    To have L{foo} be called every 15th second, and L{bar} be called
    every 20th second:

      >>> t = TickCall(5)
      >>> t.add(3, foo)
      >>> t.add(4, bar)

    Two functions that will be scheduled to be invoked on the same
    tick will be invoked in the order of addition.
    """

    def __init__(self, interval, clock=None):
        task.LoopingCall.__init__(self, self._run)
        if clock is None:
            clock = reactor
        self.clock = clock
        clock.callLater(0, self.start, interval, True)
        self.slices = list()
        self._count = 0

    def add(self, interval, fn, *args, **kw):
        """
        Add a function that will be invoked every L{interval} tick of
        the scheduler.
        """
        if interval == 0:
            raise ValueError("interval must be greater than zero")
        self.slices.append((interval, fn, args, kw))

    def _run(self):
        # run through all the slice functions one by one
        self._count += 1
        for sl, fn, args, kw in self.slices:
            if (self._count % sl) == 0:
                try:
                    fn(*args, **kw)
                except Exception, e:
                    log.deferr()


    # Support twisted 2.5:

    def _callLater(self, delay):
        self.clock.callLater(delay, self)

    def _seconds(self):
        return self.clock.seconds()

