import sys, os, AveryBot
from twisted.internet import reactor

if __name__ == "__main__":
    try:
        chan = sys.argv[1]
    except IndexError:
        print "Please specify a channel name."
        print "Example:"
        print "  python MyBot.py letstest"
    if os.path.exists('training_text.txt'):
        f = open('training_text.txt', 'r')
        for line in f:
            AveryBot.add_to_brain(line, chain_length)
        print 'Brain Reloaded'
        f.close()
    reactor.connectTCP('irc.foonetic.net', 6667, AveryBot.AveryBotFactory('#' + chan, 'Le_Bot', 2, chattiness=0.05))
    reactor.run()