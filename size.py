import markov
import pickle
import sys

m = markov.Markov(int(sys.argv[1]))
for line in open("avery.talk.TEST"):
    m.learn(line)

keys = 0
ents = 0
for k in m.ldict.keys():
    keys += 1
    ents += len(m.ldict[k])

# print("keys:", keys)
# print("ents:", ents)
print("tote:", keys + ents)
# print("bytes:", sys.getsizeof(m.ldict))
