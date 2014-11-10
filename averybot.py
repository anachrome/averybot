import random
import pickle
import configparser as cfg

import irc
from irc.bot import SingleServerIRCBot

from markov import Markov

class IRCID:
    def __init__(self, channel, nickname, realname, server, port = 6667):
        self.channel = channel
        self.nickname = nickname
        self.realname = realname
        self.server = server
        self.port = port

class AveryBot(SingleServerIRCBot):
    def __init__(self, mindfile, blfile, real_id, real, ident):
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
        self.highlights = {}

        self.channel = ident.channel    # active channel
        self.rstate = random.getstate() # random state
        self.real_id = real_id          # whether self.real is a user or a nick
        self.real = real                # real user she imitates (i.e. avery)
        #self.save_counter = 0           # write to disk every 100 talks

    # return a list of words that cannot be said by comparing the hilights
    # dict and the users currently in the channel
    def blacklist(self):
        bl = []
        users = self.channels[self.channel].users()
        for key in self.highlights:
            if self.highlights[key] in users:
                bl.append(key)
        return bl

    def talk(self):
        while True:
            sentence = self.mind.talk()
            if self.channel not in self.channels:
                print("AVEBOT ERROR: oh fuck this shouldn't actually happen")
                break
            # prevent convoing
            if sentence.startswith("!"):
                continue
            # prevent hilights
            for nope in self.blacklist():
                if nope in sentence:
                    print("cannot say because " + nope + " would highlight.  "
                        + "retrying.");
                    continue
            return sentence

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        self.do_shit(c, e, e.source.nick)

    def on_pubmsg(self, c, e):
        self.do_shit(c, e, e.target)

    def do_shit(self, c, e, target):
        text = e.arguments[0]
        if text == "@talk":
            self.rstate = random.getstate()
            c.privmsg(target, self.talk())
        elif text == "@don't":
            self.highlights[e.source.nick] = e.source.nick
            pickle.dump(self.blacklist(), open(self.blfile, 'wb'))
        elif text == "@do":
            if e.source.nick in self.highlights:
                del self.highlights[e.source.nick]
            pickle.dump(self.blacklist(), open(self.blfile, 'wb'))
        elif text == "@diag":
            c.privmsg(target, self.mind.diags)
        elif text == "@vtalk":
            self.rstate = random.getstate()
            c.privmsg(target,
                self.talk() + " [" + str(self.mind.diags) + "]")
        elif text == "@freeze":
            pickle.dump(self.rstate, open("rstate", 'wb'))
        elif text == "@thaw":
            self.rstate = pickle.load(open("rstate", 'rb'))
            random.setstate(self.rstate)
        elif text in ["@repeat", "@again"]:
            random.setstate(self.rstate)
            c.privmsg(target, self.talk())
        elif text in ["@vrepeat", "@vagain"]:
            random.setstate(self.rstate)
            c.privmsg(target,
                self.mind.talk() + " [" + str(self.mind.diags) + "]")
        elif text == "@save":
            pickle.dump(self.mind, open(self.mindfile, 'wb'))
        elif text == "@load":
            self.mind = pickle.load(open(self.mindfile, 'rb'))
        elif text in ["@quit", "@die", "@bye", "@byebye", "@fuck off"]:
            pickle.dump(self.mind, open(self.mindfile, 'wb'))
            self.die("byebye") # bug: "byebye" doesn't always do
        else: # to prevent learning commands
            if self.real_id == "user":
                source = e.source.user
            elif self.real_id == "nick":
                source = e.source.nick
            if self.real in source.lower(): # extremely fucking liberal
                self.mind.learn(text)
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

    print(server, port, channel, nickname, realname)

    aveid = IRCID(channel, nickname, realname, server, port)

    ave = AveryBot(mindfile, blfile, assimilee_id, assimilee, aveid)
    ave.start()

if __name__ == "__main__":
    main()
