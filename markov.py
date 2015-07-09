#!/usr/bin/env python3

from random import choice, shuffle
import random

import re
import pickle
import sys

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

# diagnostic class for useful information on markov-generating
class Diagnostics:
    def __init__(self, porb, branches):
        self.porb = porb
        self.branches = branches

    def __str__(self):
        return str(self.porb) + " / " + str(self.branches)

class Markov:
    def __init__(self, context, ldict = None, rdict = None):
        if ldict is None:
            ldict = ListDict()
        if rdict is None:
            rdict = ListDict()
        self.context = context
        self.ldict = ldict
        self.rdict = rdict
        self.diags = None

    def find_context(self, regex):
        # find starting [k]ontext
        ks = list(self.ldict.keys()) + list(self.rdict.keys())

        # this is a bit of a hack to make it do something sensible if the
        # dictionary is empty
        if not ks:
            return []

        shuffle(ks)

        if type(regex) == str:
            for k in ks:
                if any(map(lambda s: re.compile(regex).search(str(s)), k)):
                    return k
        elif len(regex) == self.context:
            for k in ks:
                good = True
                for el, r in zip(k, regex):
                    if not re.compile(r).search(str(el)):
                        good = False
                if good: return k

        #for k in ks:
        #    if any(map(lambda s: re.compile(regex).search(str(s)), k)): return k

        return None

    def gen(self):
        porb = 1.0
        branches = 0
        pos = 0

        # find starting [k]ontext
        ks = list(self.ldict.keys())

        # this is a bit of a hack to make it do something sensible if the
        # dictionary is empty
        if not ks:
            return []

        shuffle(ks)
        for k in ks:
            if k[0].tag_is("pos", "BEGIN"): break

        return self.gen_out(k)

    def gen_out(self, start_k):
        porb = 1.0
        branches = 0

        # yield everything in initial [k]ontext
        tokes = list(start_k)

        # go backwards first
        k = start_k
        while not k[0].tag_is("pos", "BEGIN"):
            possibs = self.rdict[k]
            next = choice(possibs)

            # diagnostics
            porb /= len(possibs)
            if len(possibs) > 1:
                branches += 1

            tokes.insert(0, next)
            k = (next,) + k[:-1]

        # yield the rest
        k = start_k
        while not k[-1].tag_is("pos", "END"):
            possibs = self.ldict[k]
            next = choice(possibs)

            # diagnostics
            porb /= len(possibs)
            if len(possibs) > 1:
                branches += 1

            tokes.append(next)
            k = k[1:] + (next,)

        self.diags = Diagnostics(porb, branches)
        return tokes


    # add a set of data (list of markov elements) to the dictionary
    def learn(self, data):
        # ignore data that doesn't add anything meaningful
        if len(data) <= self.context + 1:
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

            v = data[i]
            k = []
            for j in range(1, self.context + 1):
                k.append(data[i + j])

            k = tuple(k)
            self.rdict[k].append(v)

# helper functions for markoving irc data

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
