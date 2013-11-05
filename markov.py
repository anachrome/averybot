#!/usr/bin/env python3

from random import randrange, shuffle

# class to represent a single element in the markov dictionary
# can be either a string, or a special tag for things like the end of the data
class MarkovElem(object):
    def __init__(self, w, tags = None):
        if tags is None:
            tags = {}

        self.word = w
        self.tags = tags

    def __eq__(self, other):
        return self.word == other.word and self.tags == other.tags

    # tag predicate / validation
    def tag_is(self, tag, value = True):
        return tag in self.tags.keys() and self.tags[tag] == value

    # for use in dict (comparisons should be case insensitive)
    def __hash__(self): return hash(self.word.lower())

    def __repr__(self):
        return repr(self.word) + ':' + repr(self.tags)

    def __str__(self):
        return self.word

# a special dictionary--it basically treats uninitialized keys as empty lists
# for things like d[k].append(asdf)
class ListDict(dict):
    def __getitem__(self, key):
        if key not in self:
            super(ListDict, self).__setitem__(key, [])

        return super(ListDict, self).__getitem__(key)

# create (or add to) a markov dictionary from a set of data
def learn(data, context, dict = None):
    if dict is None:
        dict = ListDict()

    if len(data) <= context:
        return dict

    for i in range(len(data) - context):
        # generate [k]ontext and [v]alue
        k = []
        for j in range(context):
            k.append(data[i + j])
        v = data[i + context]

        # add to dictionary
        k = tuple(k)
        dict[k].append(v)

    return dict

# turn a single line of text into a list of markov elements
# (I would really like this to be a generater)
def sanitize(data):
    ret = []

    # preparatory shit
    words = []
    for word in data.split():
        elems = word.split('"')
        words.append(elems[0])

        for word in elems[1:]:
            words.append('"')
            words.append(word)
            
    quoted = False
    for word in words:
        # split off terminal punctuation
        terms = ""
        while len(word) and word[-1] in "?.!":
            terms += word[-1]
            word = word[:-1]

        elem = MarkovElem(word)

        if word == '"':
            quoted = not quoted
        else:
            elem.tags["quoted"] = quoted

        # add word to data
        ret.append(elem)
        if len(terms) > 0:
            ret.append(MarkovElem(terms, {"punc":True}))

    # these are porblematic for generatoring
    ret[0].tags["pos"] = "BEGIN"
    ret[-1].tags["pos"] = "END"

    return ret

def step(dict, k):
    possibs = dict[k]
    return possibs[randrange(len(possibs))]

def talk(dict):
    # find starting [k]ontext
    ks = list(dict.keys())
    shuffle(ks)
    for k in ks:
        if k[0].tag_is("pos", "BEGIN"): break

    # yield everything in initial [k]ontext
    for el in k:
        yield el

    # yield the rest
    while True:
        next = step(dict, k)
        yield next

        # found ending [k]ontext (?)
        k = k[1:] + (next,)
        if next.tag_is("pos", "END"): break

if __name__ == "__main__":
    mind = ListDict()
    for line in open("avery.log", "r"):
        mind = learn(sanitize(line), 2, mind)

    # for debugging
    #for e in mind:
    #   print(e, mind[e])

    for word in talk(mind):
        if word.tag_is("pos", "BEGIN"):
            print(word, end='')
        elif word.tag_is("punc"):
            print(word, end='')
        else:
            print(' ', word, sep='', end='')
    print()
