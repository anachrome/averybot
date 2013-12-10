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
    def __init__(self, mind, real, ident):
        SingleServerIRCBot.__init__(self,
            [(ident.server, ident.port)], ident.nickname, ident.nickname)
        self.channel = ident.channel
        self.mind = mind                # markov data
        self.mindfile = "avery.mem"     # file where to store that
        self.rstate = random.getstate() # random state
        self.real = real                # real user she imitates (i.e. avery)
        self.save_counter = 0           # write to disk every 100 talks

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
            c.privmsg(target, self.mind.talk())
        elif text == "@freeze":
            pickle.dump(self.rstate, open("rstate", 'wb'))
        elif text == "@thaw":
            self.rstate = pickle.load(open("rstate", 'rb'))
            random.setstate(self.rstate)
        elif text in ["@repeat", "@again"]:
            random.setstate(self.rstate)
            c.privmsg(target, self.mind.talk())
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

    try:
        mind = pickle.load(open("ave.mind", 'rb'))
    except IOError:
        print("No markov file (ave.mind); creating blank one")
        mind = Markov(2)
    aveid = IRCID(channel, nickname, server, port)

    # ave = AveryBot(mind, "averystrange", aveid)
    ave = AveryBot(mind, "averystrange", aveid)
    ave.start()

if __name__ == "__main__":
    main()
