from twisted.words.protocols import irc
from twisted.internet import protocol, reactor
from collections import defaultdict

import sys, os, random, re

markov = defaultdict(list)
STOP_WORD = "\n"

class AveryBot(irc.IRCClient):
    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)

    def signedOn(self):
        self.join(self.factory.channel)
        print "Signed on as %s." % (self.nickname,)

    def joined(self, channel):
        print "Joined %s." % (channel,)

    def privmsg(self, user, channel, msg):
        if not user:
            return
        # if self.nickname in msg:
	else:
	    msg = re.compile(self.nickname + "[:,]* ?", re.I).sub('', msg)
            prefix = "%s: " % (user.split('!', 1)[0], )
        # else:
        #    prefix = ''
        add_to_pool(msg, self.factory.chain_length, write_to_file=True)
        if prefix or random.random() <= self.factory.chattiness:
            sentence = generate_sentence(msg, self.factory.chain_length,
                self.factory.max_words)
            if sentence:
                self.msg(self.factory.channel, prefix + sentence)

class AveryBotFactory(protocol.ClientFactory):
    protocol = AveryBot

    def __init__(self, channel, nickname='Le_Bot', chain_length=3, chattiness=1.0, max_words=10000):
        self.channel = channel
        self.nickname = nickname
        self.chain_length = chain_length
        self.chattiness = chattiness
        self.max_words = max_words

    def clientConnectionLost(self, connector, reason):
        print "Lost connection (%s), reconnecting." % (reason,)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Could not connect: %s" % (reason,)
    
def add_to_pool(msg, chain_length, write_to_file=False):
    if write_to_file:
        f = open('avery_text.log', 'a')
        f.write(msg + '\n')
        f.close()
    buf = [STOP_WORD] * chain_length
    for word in msg.split():
        markov[tuple(buf)].append(word)
        del buf[0]
        buf.append(word)
    markov[tuple(buf)].append(STOP_WORD)
    
def generate_sentence(msg, chain_length, max_words=10000):
    buf = msg.split()[:chain_length]
    
    if len(msg.split()) > chain_length:
        message = buf[:]
    for i in xrange(max_words):
        try:
            next_word = random.choice(markov[tuple(buf)])
        except IndexError:
            continue
        if next_word == STOP_WORD:
            break
        message.append(next_word)
        del buf[0]
        buf.append(next_word)
    return ' '.join(message)
    
if __name__ == "__main__":
    try:
        chan = sys.argv[1]
    except IndexError:
        print "Please specify a channel name."
        print "Example:"
        print "  python MyBot.py letstest"
    if os.path.exists('avery_text.log'):
        f = open('avery_text.log', 'r')
        for line in f:
            add_to_pool(line, 2)
        print 'Pool Refilled'
        f.close()
    reactor.connectTCP('irc.foonetic.net', 6667, AveryBotFactory('#' + chan, 'Le_Bot', 2, chattiness=0.05))
    reactor.run()