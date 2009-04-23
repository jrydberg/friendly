from zope.interface import Interface


class IContactImporter(Interface):

    def importContacts(username, password, progress):
        """
        Import contacts.

        Returns a deferred that will be called with a list of
        dictionaries.
        """
