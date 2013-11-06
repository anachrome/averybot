import irc
from irc.bot import SingleServerIRCBot

import markov

mind = markov.ListDict()
for line in open("avery.log", "r"):
    mind = markov.learn(markov.sanitize(line), 2, mind)

class AveryBot(SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        self.do_shit(c, e.source.nick, e.arguments[0])

    def on_pubmsg(self, c, e):
        self.do_shit(c, e.target, e.arguments[0])

    def do_shit(self, c, target, text):
        if text == "@talk":
            response = ""
            for word in markov.talk(mind):
                if word.tag_is("pos", "BEGIN"):
                    response += str(word)
                elif word.tag_is("punc"):
                    response += str(word)
                else:
                    response += (" " + str(word))
            c.privmsg(target, response)

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

    ave = AveryBot(channel, nickname, server, port)
    ave.start()

if __name__ == "__main__":
    main()
