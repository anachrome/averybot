import markov
import pickle
import sys

m = markov.Markov(int(sys.argv[1]))
for line in open("avery.talk"):
    m.learn(line)

print(sys.getsizeof(m.ldict))
