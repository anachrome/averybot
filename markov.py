#!/usr/bin/env python3

from random import choice, shuffle

import re
import pickle

# class to represent a single element in the markov dictionary
# can be either a string, or a special tag for things like the end of the data
class MarkovElem(object):
    def __init__(self, w, tags = None):
        if tags is None:
            tags = {}

        self.word = w
        self.tags = tags

    # tag predicate / validation
    def tag_is(self, tag, value = True):
        return tag in self.tags.keys() and self.tags[tag] == value

    # for use in dict (comparisons should be case insensitive)
    def __hash__(self): return hash(self.word.lower())

    def __eq__(self, other):
        return self.word == other.word and self.tags == other.tags

    # for showing
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

# turn a single line of text into a list of markov elements
# (I would really like this to be a generater)
def sanitize(data):
    ret = []

    # preparatory shit
    words = []
    for word in data.split():
        def choice(*strs):
            return '(' + '|'.join(strs) + ')'
        oparen = '^\(|(?<=[^:])\('
        cparen = '^\(|(?<=[^:])\)'
        words += filter(lambda x: x != "",
            re.split(choice(oparen, cparen, '"'), word))

    quoted = False
    parendepth = 0
    for word in words:
        # split off terminal punctuation
        terms = ""
        while len(word) and word[-1] in "?.!":
            terms += word[-1]
            word = word[:-1]

        if word != "":
            elem = MarkovElem(word)

            if word == '"':
                quoted = not quoted
                if quoted:
                    elem.tags["parenthesque"] = "open"
                else:
                    elem.tags["parenthesque"] = "close"
            else:
                elem.tags["quoted"] = quoted

            if word == '(':
                elem.tags["parendepth"] = parendepth
                elem.tags["parenthesque"] = "open"
                parendepth += 1
            elif word == ')':
                parendepth -= 1
                elem.tags["parenthesque"] = "close"
                elem.tags["parendepth"] = parendepth
            else:
                elem.tags["parendepth"] = parendepth

            # add word to data
            ret.append(elem)

        # terminal punctuation gets added now
        if len(terms) > 0:
            ret.append(MarkovElem(terms, {"punc":True}))

    # these are porblematic for generatoring
    ret[0].tags["pos"] = "BEGIN"
    ret[-1].tags["pos"] = "END"

    return ret

# inverse of sanitize--turns a list of markov elements into a string
def prettify(data):
    pretty = ""

    quoted = False
    for word in data:
        if word.tag_is("punc"):
            pretty = pretty[:-1] + str(word) + ' '
        elif word.tag_is("parenthesque", "open"):
            pretty += str(word)
        elif word.tag_is("parenthesque", "close"):
            pretty = pretty[:-1] + str(word) + ' '
        elif word.tag_is("pos", "END"):
            pretty += str(word)
        else:
            pretty += (str(word) + ' ')

        # if word.tag_is("pos", "BEGIN"):
        #     pretty += str(word)
        # elif word.tag_is("punc"):
        #     pretty += str(word)
        # else:
        #     pretty += (" " + str(word))

    return pretty


class Markov(object):
    def __init__(self, context, ldict = None):
        if ldict is None:
            ldict = ListDict()
        self.context = context
        self.ldict = ldict

    # add a set of data (list of markov elements) to the dictionary
    def feed(self, data):
        if len(data) <= self.context:
            return

        for i in range(len(data) - self.context):
            # generate [k]ontext and [v]alue
            k = []
            for j in range(self.context):
                k.append(data[i + j])
            v = data[i + self.context]

            # add to ldictionary
            k = tuple(k)
            self.ldict[k].append(v)

    def learn(self, str):
        self.feed(sanitize(str))

    def gen(self, minlen = 0, maxlen = 0):
        pos = 0

        # find starting [k]ontext
        ks = list(self.ldict.keys())
        shuffle(ks)
        for k in ks:
            if k[0].tag_is("pos", "BEGIN"): break

        # yield everything in initial [k]ontext
        for el in k:
            yield el

        # yield the rest
        while True:
            pos += 1

            possibs = self.ldict[k]
            # if pos < minlen:
            #     contsibs = list(filter(lambda x: not x.tag_is("pos", "END"),
            #         possibs))
            #     if len(contsibs) > 0:
            #         possibs = contsibs
            # if maxlen != 0 and pos >= maxlen:
            #     endsibs = list(filter(lambda x: x.tag_is("pos", "END"),
            #         possibs))
            #     if len(endsibs) > 0:
            #         possibs = endsibs
            next = choice(possibs)

            # next = self.ldict[k][randrange(len(self.ldict[k]))]
            yield next

            # found ending [k]ontext (?)
            k = k[1:] + (next,)
            if next.tag_is("pos", "END"): break

    def talk(self):
        return prettify(self.gen())

if __name__ == "__main__":
    # ave = Markov(2)
    # for line in open("avery.log", 'r'):
    #     ave.learn(line)
    ave = pickle.load(open("avery.mem", 'rb'))

    # for debugging
    #for e in ave.ldict:
    #  print(e, ave.ldict[e])

    # out = []
    # while len(out) != 10:
    #     out = list(ave.gen())
    # print(prettify(out))
    # for word in ave.gen():
    #     print(repr(word))
    print(ave.talk())
