import configparser as cfg
import datetime
import pickle
import queue
import random
import re
import string
import threading
import time

import irc
from irc.bot import SingleServerIRCBot

import markov
from markov import Markov, MarkovElem

class IRCID:
    def __init__(self, channel, cafe, nickname, realname, server, port = 6667, password = ""):
        self.channel = channel
        self.cafe = cafe
        self.nickname = nickname
        self.realname = realname
        self.server = server
        self.port = port
        self.password = password

class AveryBot(SingleServerIRCBot):
    def __init__(self, mindfile, blfile, logfile, agefile,
        real_id, real, ident, birthday, friend):
        SingleServerIRCBot.__init__(self,
            [(ident.server, ident.port)], ident.nickname, ident.realname)

        self.mindfile = mindfile
        self.blfile = blfile
        self.logfile = logfile
        self.agefile = agefile
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
        
        self.waiting_for_friend = queue.Queue() # channels to send lurkers to

        self.nick = ident.nickname
        self.password = ident.password
        self.channel = ident.channel    # active channels
        self.cafe = ident.cafe
        self.rstate = random.getstate() # random state
        self.real_id = real_id          # whether self.real is a user or a nick
        self.real = real                # real user she imitates (i.e. avery)
        #self.save_counter = 0           # write to disk every 100 talks
        self.friend = friend
        self.birthday = birthday

    def at_bday(self, birthday):
        now = datetime.datetime.today()
        bday = self.birthday.replace(year = now.year)
        if bday <= now: bday = bday.replace(year = bday.year + 1)
        print("next birthday:", bday)

        bday_action = threading.Timer((bday - now).total_seconds(), birthday)
        bday_action.daemon=True
        bday_action.start()

    def on_welcome(self, c, e):
        c.mode(self.nick, '+B-x')
        c.privmsg("NickServ", "IDENTIFY " + self.password)
        for channel in self.channel:
            c.join(channel)
        c.join(self.cafe)

        def birthday():
            age = int(open(self.agefile, 'r').read()) + 1
            c.action(self.cafe, "is %s years old today!" % age)
            print(age, file=open(self.agefile, 'w'))
            self.at_bday(birthday)

        self.at_bday(birthday)

    # cache each channel's mode
    def on_join(self, c, e):
        if e.source.nick == self.nick:
            c.mode(e.target, "")

    # basically borrowed from irc.bot.py's _on_mode(), since this library is a
    # god damn piece of shit
    def on_channelmodeis(self, c, e):
        modes = irc.modes.parse_channel_modes(e.arguments[1])
        t = e.arguments[0]
        ch = self.channels[t]
        for mode in modes:
            if mode[0] == '+':
                f = self.channels[t].set_mode(mode[1], mode[2])
            else:
                f = self.channels[t].clear_mode(mode[1], mode[2])

    def talk(self, args, diag=False):
        for i in range(3):
            if len(args) == 0:
                sentence = markov.prettify(self.mind.gen(), diag)
            elif len(args) == 1:
                k = self.mind.find_context(args[0])
                if k is not None:
                    sentence = markov.prettify(self.mind.gen_out(k), diag)
                else:
                    return "i don't know anything about " + args[0]
            elif len(args) == 2:
                k = self.mind.find_context(args)
                if k is not None:
                    sentence = markov.prettify(self.mind.gen_out(k), diag)
                else:
                    return "i don't know anything about " + " ".join(args)

            else:
                return "i can only talk about one (or maybe two) things at a time"

            for channel in self.channel:
                if channel not in self.channels:
                    print("AVEBOT ERROR: oh fuck this shouldn't actually happen")
                    return "i broke"

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

    def on_privmsg(self, c, e):
        print("RECEIVED:", e.arguments[0])
        if (e.source.nick == self.friend):
            if not self.waiting_for_friend.empty():
                c.privmsg(self.waiting_for_friend.get(), e.arguments[0])
            else:
                print("somebody's lurking!...")
        else: # friends don't tell friends what to do
            self.do_shit(c, e, e.source.nick)

    def on_action(self, c, e):
        print(e.target)
        if (irc.client.is_channel(e.target)): # this irc library is a PoFS
            return
        if (e.source.nick == self.friend):
            if not self.waiting_for_friend.empty():
                c.privmsg(self.waiting_for_friend.get(), e.arguments[0])
            else:
                print("somebody's lurking!...")
        else: # friends don't tell friends what to do
            self.do_shit(c, e, e.source.nick)

    def on_pubmsg(self, c, e):
        self.do_shit(c, e, e.target)

    def do_shit(self, c, e, target):
        text = e.arguments[0]
        print(repr(text))

        command = ""
        if target == self.cafe:
            if text.split()[0].strip(string.punctuation) in ["averbot", "averybot"]:
                command = text.split()[1]
                args = text.split()[2:]
        else:
            if text[0] == '@':
                command = text.split()[0][1:]
                args = text.split()[1:]

        if command:
            #command = text.split()[0]
            #args = text.split()[1:]
            if command == "talk":
                self.states[target] = random.getstate()
                c.privmsg(target, self.talk(args))
            elif command == "sing":
                if target in channels and self.channels[target].has_mode("C"):
                    c.privmsg(target, "Aesthetic freedom is like free speech; it is, indeed, a form of free speech.")
                    c.privmsg(target, "and when the rights of free speech and free press are at risk, all of the other liberties we hold dear are endangered.")
                self.states[target] = random.getstate()
                raw = self.talk(args)
                out = []
                # experimental ansi color shit
                #for word in raw.split():
                #    out.append("\033[0" + str(random.randrange(2))
                #             + ";3"     + str(random.randrange(8))
                #             + "m"      + word
                #             + "\033[00;00m")
                #print(repr(" ".join(out)))
                #c.privmsg(target, " ".join(out))
                for word in raw.split():
                    out.append("\x03" + str(random.randrange(16)) + word)
                c.privmsg(target, " ".join(out) + "\x03")
            elif command == "bees":
                self.states[target] = random.getstate()
                c.privmsg(target, self.talk(["swamp", "monsters"]).replace("bees", "\x02bees\x02"))
            elif command == "sin":
                self.states[target] = random.getstate()
                sin = random.choice(["lust", "gluttony",
                    "greed", "sloth", "wrath", "envy", "pride"])
                sin = "".join("[" + "".join(j) + "]" for j in zip(sin.lower(), sin.upper()))
                c.privmsg(target, self.talk([sin]))
            elif command == "bee":
                c.privmsg(target, "there is never just one...");
            elif command == "send":
                e.arguments = [" ".join(args[1:])]
                self.do_shit(c, e, args[0])
            elif command == "don't":
                self.blacklist.append(e.source.nick)
                pickle.dump(self.blacklist, open(self.blfile, 'wb'))
            elif command == "do":
                if e.source.nick in self.blacklist:
                    self.blacklist.remove(e.source.nick)
                pickle.dump(self.blacklist, open(self.blfile, 'wb'))
            elif command in ["blacklist", "bl"]:
                c.privmsg(e.source.nick, ", ".join(self.blacklist))
            elif command == "diag":
                c.privmsg(target, self.mind.diags)
            elif command == "vtalk":
                self.states[target] = random.getstate()
                c.privmsg(target,
                    self.talk(args, True) + " [" + str(self.mind.diags) + "]")
            elif command == "freeze":
                pickle.dump(self.states, open("rstate", 'wb'))
            elif command == "thaw":
                self.states = pickle.load(open("rstate", 'rb'))
                random.setstate(self.rstate)
            elif command in ["repeat", "again"]:
                temp = random.getstate()
                random.setstate(self.states[e.source.nick])
                c.privmsg(target, self.talk(args))
                random.setstate(temp)
            elif command in ["vrepeat", "vagain", "vagina"]:
                temp = random.getstate()
                random.setstate(self.states[e.source.nick])
                c.privmsg(target,
                    self.talk(args, True) + " [" + str(self.mind.diags) + "]")
                random.setstate(temp)
            elif command == "save":
                pickle.dump(self.mind, open(self.mindfile, 'wb'))
            elif command == "load":
                self.mind = pickle.load(open(self.mindfile, 'rb'))
            elif command in ["quit", "die", "bye", "byebye", "fuck"]:
                pickle.dump(self.mind, open(self.mindfile, 'wb'))
                msg = ":(" if command == "@fuck" else "byebye"
                self.die(msg) # bug: "byebye" doesn't always do
            elif command == "help":
                c.privmsg(target, "naw, but feel free to check out my @source ;)")
            elif command == "source":
                c.privmsg(target, "https://github.com/anachrome/averybot")
            elif command == "george":
                c.privmsg(target,
                    "".join(i + "\x02" if i != 'g' else i
                        for i in "wow i'm a color hating fascist"))
            elif command == "nbsp":
                c.privmsg(target, "!convo grep Е")
            elif command in ["convo", "hug", "static", "fm", "alert"]:
                print(self.friend, "!" + command + " " + " ".join(args))
                self.waiting_for_friend.put(target)
                c.privmsg(self.friend, ("!" + command + " " + " ".join(args)).strip())
            elif command[0] == "!": # ignore lurkers
                pass
            else:
                command = ""

        if not command: # to prevent learning commands
            if self.real_id == "user":
                source = e.source.user
            elif self.real_id == "nick":
                source = e.source.nick
            if self.real in source.lower(): # extremely fucking liberal
                self.mind.learn(markov.sanitize(text))
                print(text, file=open(self.logfile, 'a'))
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
    channel = config["channels"].split()
    cafe = config["cafe"]
    nickname = config["nickname"]
    realname = config["realname"]
    password = config["password"]

    assimilee_id = config["assimilee_id"]
    assimilee = config["assimilee"]

    birthday = datetime.datetime.strptime(config["birthday"], "%m/%d %H:%M:%S")
    agefile = config["agefile"]

    mindfile = config["mindfile"]
    blfile = config["blfile"]
    logfile = config["logfile"]

    friend = config["friend"]

    print(server, port, channel, cafe, nickname, realname, friend)

    aveid = IRCID(channel, cafe, nickname, realname, server, port, password)

    ave = AveryBot(mindfile, blfile, logfile, agefile,
        assimilee_id, assimilee, aveid, birthday, friend)
    ave.start()

if __name__ == "__main__":
    main()
