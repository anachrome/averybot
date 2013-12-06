import random
import pickle

import irc
from irc.bot import SingleServerIRCBot

from markov import Markov

class AveryBot(SingleServerIRCBot):
    def __init__(self, mind, channel, nickname, server, port=6667):
        SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.mind = mind
        self.rstate = random.getstate()

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        self.do_shit(c, e.source.nick, e.arguments[0])

    def on_pubmsg(self, c, e):
        self.do_shit(c, e.target, e.arguments[0])

    def do_shit(self, c, target, text):
        if text == "@talk":
            self.rstate = random.getstate()
            c.privmsg(target, self.mind.talk())
        elif text == "@freeze":
            pickle.dump(self.rstate, open('asdf', 'wb'))
        elif text == "@thaw":
            self.rstate = pickle.load(open('asdf', 'rb'))
            random.setstate(self.rstate)
        elif text in ["@repeat", "@again"]:
            random.setstate(self.rstate)
            c.privmsg(target, self.mind.talk())

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

    mind = Markov(2)
    for line in open("avery.log", 'r'):
        mind.learn(line)

    ave = AveryBot(mind, channel, nickname, server, port)
    ave.start()

if __name__ == "__main__":
    main()
