#!/usr/bin/env python3

# a script to turn a list of lines into a serialized markov dictionary
import sys
import pickle
import markov

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("usage: " + sys.argv[0] + " <source> <dest> [<order> = 2]")
    src = sys.argv[1]
    dst = sys.argv[2]
    order = 2
    if len(sys.argv) == 4:
        order = int(sys.argv[3])

    mark = markov.Markov(order)
    for line in open(src, 'r'):
        mark.learn(line)

    pickle.dump(mark, open(dst, 'wb'))
