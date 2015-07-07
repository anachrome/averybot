#!/usr/bin/env python3

import sys

logfile = sys.argv[1]

def strippref(line):
    return line[line.find(">") + 2:]

peoples = {}

for line in open(logfile, "r"):
    # not a talking line
    if line[0] != "<":
        continue

    # find who is talking and what they say
    endwaka = line.find(">")
    person = line[0:endwaka + 1]
    line = line[endwaka + 2:]

    # write
    if person not in peoples.keys():
        peoples[person] = open(person + ".log", "w")
    peoples[person].write(line)
