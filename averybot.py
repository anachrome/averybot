import random
import pickle
import configparser as cfg
import re

import irc
from irc.bot import SingleServerIRCBot

import markov
from markov import Markov, MarkovElem

class IRCID:
    def __init__(self, channel, nickname, realname, server, port = 6667):
        self.channel = channel
        self.nickname = nickname
        self.realname = realname
        self.server = server
        self.port = port

class AveryBot(SingleServerIRCBot):
    def __init__(self, mindfile, blfile, real_id, real, ident, friend):
        SingleServerIRCBot.__init__(self,
            [(ident.server, ident.port)], ident.nickname, ident.realname)

        self.mindfile = mindfile
        self.blfile = blfile
        # load mind
        try:
            self.mind = pickle.load(open(mindfile, 'rb'))
        except IOError:
            print("No markov file (" + mindfile + ") found; making a blank one")
            self.mind = Markov(2)

        # words that will highlight some nicks, in the form of a dictionary
        # from words to the nicks they hilight.
        try:
            self.blacklist = pickle.load(open(self.blfile, "rb"))
        except FileNotFoundError:
            self.blacklist = []

        class State(dict):
            def __getitem__(self, key):
                if key not in self:
                    super(State, self).__setitem__(key, random.getstate())

                return super(State, self).__getitem__(key)

        # the handle generator
        self.handlegen = Markov(2)
        for line in open("nicks", "r"):
            line = line[:-1] # strip newl
            n = []
            for c in line:
                n.append(MarkovElem(c))

            #n = map(MarkovElem, line)

            n[0].tags["pos"] = "BEGIN"
            n[-1].tags["pos"] = "END"

            self.handlegen.learn(n)

        try:
            self.states = pickle.load(open("rstate", "rb"))
        except FileNotFoundError:
            self.states = State()

        self.channel = ident.channel    # active channel
        self.rstate = random.getstate() # random state
        self.real_id = real_id          # whether self.real is a user or a nick
        self.real = real                # real user she imitates (i.e. avery)
        #self.save_counter = 0           # write to disk every 100 talks
        self.friend = friend

    def talk(self, args):
        for i in range(3):
            if len(args) == 0:
                sentence = markov.prettify(self.mind.gen())
            elif len(args) == 1:
                k = self.mind.find_context(args[0])
                if k is not None:
                    sentence = markov.prettify(self.mind.gen_out(k))
                else:
                    return "i don't know anything about " + args[0]
            elif len(args) == 2:
                k = self.mind.find_context(args)
                if k is not None:
                    sentence = markov.prettify(self.mind.gen_out(k))
                else:
                    return "i don't know anything about " + " ".join(args)

            else:
                return "i can only talk about one (or maybe two) things at a time"

            if self.channel not in self.channels:
                print("AVEBOT ERROR: oh fuck this shouldn't actually happen")
                break

            # catch line length
            if len(sentence) > 450: # this should probably be good
                print("message too long.  retrying")
                continue

            # prevent convoing
            if sentence.startswith("!"):
                continue

            # prevent hilights
            tryagain = False
            for nope in self.blacklist:
                # generate non-blacklisted nick
                try_again = True
                while try_again:
                    new = "".join(map(str, self.handlegen.gen()))
                    try_again = False
                    for bad in self.blacklist:
                        if new.lower() == bad.lower():
                            try_again = True
                print("replacing", nope, "with", new)

                sentence = sentence.replace(nope, new)

            return sentence
        return "it's too hard :("

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        if (e.source.nick == self.friend):
            c.privmsg(self.channel, e.arguments[0])
        self.do_shit(c, e, e.source.nick)

    def on_action(self, c, e):
        print(e.target)
        if (irc.client.is_channel(e.target)): # this irc library is a PoFS
            return
        if (e.source.nick == self.friend):
            c.privmsg(self.channel, self.friend + " " + e.arguments[0])
        self.do_shit(c, e, e.source.nick)

    def on_pubmsg(self, c, e):
        self.do_shit(c, e, e.target)

    def do_shit(self, c, e, target):
        text = e.arguments[0]
        print(repr(text))

        command = text.split()[0]
        args = text.split()[1:]
        if command == "@talk":
            self.states[target] = random.getstate()
            c.privmsg(target, self.talk(args))
        elif command == "@bees":
            self.states[target] = random.getstate()
            c.privmsg(target, self.talk(["bees"]).replace("bees", "\x02bees\x02"))
        elif command == "@bee":
            c.privmsg(target, "there is never just one...");
        elif command == "@send":
            e.arguments = [" ".join(args[1:])]
            self.do_shit(c, e, args[0])
        elif command == "@don't":
            self.blacklist.append(e.source.nick)
            pickle.dump(self.blacklist, open(self.blfile, 'wb'))
        elif command == "@do":
            if e.source.nick in self.blacklist:
                self.blacklist.remove(e.source.nick)
            pickle.dump(self.blacklist, open(self.blfile, 'wb'))
        elif command in ["@blacklist", "@bl"]:
            c.privmsg(e.source.nick, ", ".join(self.blacklist))
        elif command == "@diag":
            c.privmsg(target, self.mind.diags)
        elif command == "@vtalk":
            self.states[target] = random.getstate()
            c.privmsg(target,
                self.talk(args) + " [" + str(self.mind.diags) + "]")
        elif command == "@freeze":
            pickle.dump(self.states, open("rstate", 'wb'))
        elif command == "@thaw":
            self.states = pickle.load(open("rstate", 'rb'))
            random.setstate(self.rstate)
        elif command in ["@repeat", "@again"]:
            temp = random.getstate()
            random.setstate(self.states[e.source.nick])
            c.privmsg(target, self.talk(args))
            random.setstate(temp)
        elif command in ["@vrepeat", "@vagain"]:
            temp = random.getstate()
            random.setstate(self.states[e.source.nick])
            c.privmsg(target,
                self.talk(args) + " [" + str(self.mind.diags) + "]")
            random.setstate(temp)
        elif command == "@save":
            pickle.dump(self.mind, open(self.mindfile, 'wb'))
        elif command == "@load":
            self.mind = pickle.load(open(self.mindfile, 'rb'))
        elif command in ["@quit", "@die", "@bye", "@byebye", "@fuck"]:
            pickle.dump(self.mind, open(self.mindfile, 'wb'))
            msg = ":(" if command == "@fuck" else "byebye"
            self.die(msg) # bug: "byebye" doesn't always do
        elif command == "@help":
            c.privmsg(target, "naw, but feel free to check out my @source ;)")
        elif command == "@source":
            c.privmsg(target, "https://github.com/anachrome/averybot")
        elif command == "@george":
            c.privmsg(target,
                "".join(i + "\x02" if i != 'g' else i
                    for i in "wow i'm a color hating fascist"))
        elif command in ["@convo", "@hug", "@static", "@fm"]:
            print(self.friend, "!" + command[1:] + " " + " ".join(args))
            c.privmsg(self.friend, ("!" + command[1:] + " " + " ".join(args)).strip())
        elif command[0] == "!": # ignore lurkers
            pass
        else: # to prevent learning commands
            if self.real_id == "user":
                source = e.source.user
            elif self.real_id == "nick":
                source = e.source.nick
            if self.real in source.lower(): # extremely fucking liberal
                self.mind.learn(markov.sanitize(text))
                pickle.dump(self.mind, open(self.mindfile, 'wb'))

def main():
    import sys
    if len(sys.argv) != 2:
        print("usage: ./averybot.py <config>")
        sys.exit(1)

    cfgp = cfg.ConfigParser()
    cfgp.read(sys.argv[1])

    config = cfgp["averybot"]

    server = config["server"]
    port   = int(config["port"])
    channel = config["channel"]
    nickname = config["nickname"]
    realname = config["realname"]

    assimilee_id = config["assimilee_id"]
    assimilee = config["assimilee"]

    mindfile = config["mindfile"]
    blfile = config["blfile"]

    friend = config["friend"]

    print(server, port, channel, nickname, realname, friend)

    aveid = IRCID(channel, nickname, realname, server, port)

    ave = AveryBot(mindfile, blfile, assimilee_id, assimilee, aveid, friend)
    ave.start()

if __name__ == "__main__":
    main()
