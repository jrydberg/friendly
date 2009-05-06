from random import shuffle


class RandomPickIterator:

    def __init__(self, picker):
        self.picker = picker
        self.pieces = None
        self.fixed = 0

    def next(self):
        if self.fixed < len(self.picker.fixed):
            self.fixed += 1
            return self.picker.fixed[self.fixed - 1]
        if self.pieces is None:
            self.pieces = list()
            for interests in self.picker.interests[1:]:
                self.pieces.extend(interests)
            shuffle(self.pieces)
        if not self.pieces:
            raise StopIteration
        return self.pieces.pop()


class PiecePicker:
    """
    """

    def __init__(self, num):
        self.num = num
        self.interests = [list(range(num))]
        self.fixed = list()
        
    def gotHave(self, index):
        """
        Report to the picker that the piece with the given index
        is available through on of the peers.
        """
        c = 0
        while c < len(self.interests):
            if index in self.interests[c]:
                break
            c += 1
        if c == len(self.interests) - 1:
            self.interests.append(list())
        self.interests[c].remove(index)
        self.interests[c + 1].append(index)

    def lostHave(self, index):
        """
        Report to the picker that the piece with the given index is no
        longer available through one of the peers.

        It still may be available through some other peer.
        """
        c = 0
        for c in range(len(self.interests)):
            if index in self.interests[c]:
                break
        if c == 0:
            return
        self.interests[c].remove(index)
        self.interests[c - 1].append(index)

    def chunkReceived(self, piece):
        if not piece in self.fixed:
            self.fixed.append(piece)

    def complete(self, piece):
        self.fixed.remove(piece)

    def __iter__(self):
        return RandomPickIterator(self)

