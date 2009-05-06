from overlay.probe import SimplestProbeManager


class Connector(SimplestProbeManager):

    def __init__(self, overlayController, q, factory):
        SimplestProbeManager.__init__(self, overlayController, q,
                                      factory)
