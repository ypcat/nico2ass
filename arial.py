#!/usr/bin/env python3

import collections
import json
import os
import shutil
import sys

from fontTools import ttLib

json_fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'arial.json')
ttf_fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'arial.ttf')

def get_table():
    if not os.path.exists(json_fn):
        tt = ttLib.TTFont(ttf_fn)
        with open(json_fn, 'w') as f:
            json.dump([chr(c) for t in tt['cmap'].tables for c in t.cmap.keys()], f)
    return collections.defaultdict(lambda:'[tofu]', {ord(c):c for c in json.load(open(json_fn))})

def translate(fn, table):
    orig_fn = f'{fn}.orig'
    if not os.path.exists(orig_fn):
        shutil.copy2(fn, orig_fn)
    with open(fn, 'w') as f:
        for line in open(orig_fn):
            f.write(line.rstrip().translate(table) + '\n')

def main():
    table = get_table()
    for fn in sys.argv[1:]:
        print(fn)
        translate(fn, table)

if __name__ == '__main__':
    main()

