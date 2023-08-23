#!/usr/bin/env python3

import json

dump = json.load(open('apis_dump.json'))

for i,d in enumerate(dump):
    fname = "dumps/{:05d}.json".format(i)
    with open(fname, 'w') as f:
        f.write(json.dumps(d))
