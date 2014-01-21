import random
import pickle

import irc
from irc.bot import SingleServerIRCBot

from markov import Markov

class IRCID:
    def __init__(self, channel, nickname, server, port = 6667):
        self.channel = channel
        self.nickname = nickname
        self.server = server
        self.port = port

class AveryBot(SingleServerIRCBot):
    def __init__(self, mindfile, real, ident):
        SingleServerIRCBot.__init__(self,
            [(ident.server, ident.port)], ident.nickname, ident.nickname)

        # load mind
        try:
            self.mind = pickle.load(open(mindfile, 'rb'))
        except IOError:
            print("No markov file (ave.mind); creating blank one")
            self.mind = Markov(2)

        # words that will highlight some nicks, in the form of a dictionary
        # from words to the nicks they hilight.
        self.highlights = {}

        self.channel = ident.channel    # active channel
        self.rstate = random.getstate() # random state
        self.real = real                # real user she imitates (i.e. avery)
        self.save_counter = 0           # write to disk every 100 talks

    # return a list of words that cannot be said by comparing the hilights
    # dict and the users currently in the channel
    def blacklist():
        bl = []
        users = self.channels[self.channel].users()
        for (key,val) in highlights:
            if val in users:
                bl.append(key)
        return bl

    def talk(self):
        while True:
            sentence = self.mind.talk()
            if self.channel not in self.channels:
                print("AVEBOT ERROR: oh fuck this shouldn't actually happen")
                break
            # prevent convoing
            if sentence[0] == '!':
                continue
            # prevent hilights
            for nope in blacklist():
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
        elif text == "@diag":
            c.privmsg(target, self.mind.diags)
        elif text == "@vtalk":
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
            if e.source.nick == self.real:
                self.mind.learn(text)
                pickle.dump(self.mind, open(self.mindfile, 'wb'))

def main():
    import sys
    if len(sys.argv) != 4:
        print("blah blha wornf argunamas")
        sys.exit(1)

    s = sys.argv[1].split(":", 1)
    server = s[0]
    if len(s) == 2:
        try:
            port = int(s[1])
        except ValueError:
            print("bad port")
            sys.exit(1)
    else:
        port = 6667
    channel = sys.argv[2]
    nickname = sys.argv[3]

    aveid = IRCID(channel, nickname, server, port)

    # ave = AveryBot(mind, "averystrange", aveid)
    ave = AveryBot("avery.mem", "averystrange", aveid)
    ave.start()

if __name__ == "__main__":
    main()
