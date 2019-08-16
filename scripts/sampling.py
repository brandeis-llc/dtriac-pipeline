#! /usr/bin/env python3

from sys import argv
import re
import os
import random

def sample(txt_data_dir, filesize_cap):
    filtered_files = [fname for fname in 
            filter(
                lambda x: x.endswith(".txt") and os.path.getsize(os.path.join(txt_data_dir, x)) < filesize_cap,
                os.listdir(txt_data_dir))
            ]
    random.shuffle(filtered_files)
    return filtered_files

def parsesize(size_str):
    units = {"b": 1, "k": 10**3, "m": 10**6, "g": 10**9, "t": 10**12}
    parsed = re.match(r'([.,\d]+)([a-z]?)', size_str).groups()
    number = parsed[0]
    unit = 'b' 
    if len(parsed) == 2:
        if parsed[1] in units.keys():
            unit = parsed[1]
        #  else:
            #  print("unit is not recognizable and will be ignored: " + parsed[1])
    return(float(number)*units[unit])

if __name__ == "__main__":
    txt_dir = argv[1] 
    filesize_cap = parsesize(argv[2]) if len(argv) > 2 else float('inf')
    sample_size = int(argv[3]) if len(argv) > 3 else 25

    for f in (sample(txt_dir, filesize_cap)[:sample_size]):
        print(f)
