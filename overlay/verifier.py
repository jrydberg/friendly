from twisted.internet import defer
from overlay.friend import Friend


class PublicFriendVerifier:
    """
    Friend verifier that can be used for public swarm networks.
    """

    def verifyFriend(self, certificate):
        return defer.succeed(Friend(certificate))


