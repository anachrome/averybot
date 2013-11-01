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

    # predicates
    def isbegin():
        return self.tags["pos"] == "BEGIN"
    def isend():
        return self.tags["pos"] == "END"

    # for use in dict
    def __hash__(self): return hash(self.word.lower())

    def __repr__(self):
        return '"' + self.word + '":' + repr(self.tags)

    def __str__(self):
        return self.word

def MarkovPunc(w, tags = None):
    if tags is None:
        tags = {}

    tags["punc"] = True
    return MarkovElem(w, tags)

def MarkovPos(w, pos, tags = None):
    if tags is None:
        tags = {}

    tags["pos"] = pos
    return MarkovElem(w, tags)

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
def sanitize(data):
    ret = []
    for word in data.split():
        # split off terminal punctuation
        terms = ""
        while len(word) and word[-1] in "?.!":
            terms += word[-1]
            word = word[:-1]

        # # desensitize words (to case)
        # word = word.lower()

        ret.append(MarkovElem(word))
        if len(terms) > 0:
            ret.append(MarkovPunc(terms))

    # print(ret)

    ret[0].tags["pos"] = "BEGIN"
    ret[-1].tags["pos"] = "END"

    return ret

def step(dict, k):
    possibs = dict[k]
    return possibs[randrange(len(possibs))]

def talk(dict, k):
    for el in k:
        yield el

    while True:
        next = step(dict, k)
        yield next

        k = k[1:] + (next,)
        if "pos" in next.tags.keys() and next.tags["pos"] == "END": break

def pickstart(dict):
    ks = list(dict.keys())
    shuffle(ks)
    for k in ks:
        if "pos" in k[0].tags.keys() and k[0].tags["pos"] == "BEGIN":
            return k

mind = ListDict()
for line in open("avery.log", "r"):
    mind = learn(sanitize(line), 2, mind)

# for e in mind:
#     print(e, mind[e])

for word in talk(mind, pickstart(mind)):
    if "pos" in word.tags.keys() and word.tags["pos"] == "BEGIN":
        print(word, end='')
    elif "punc" in word.tags.keys() and word.tags["punc"]:
        print(word, end='')
    else:
        print(' ', word, sep='', end='')
print()
