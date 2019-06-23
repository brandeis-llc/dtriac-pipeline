"""generate_statistics.py

Create some statistics and save them in a JSON file named stats.json. This file
should be put in the site/data directory, where it can be used by the Flask
site.

Usage:

$ python generate_statistics.py DIRECTORY

DIRECTORY contains JSON files created for documents (not sentences) by
create_index_docs.py.

"""

import os, sys, glob, json, codecs
from collections import Counter


def write_statistics(directory, outfile):
    years = Counter()
    topics = Counter()
    directory = sys.argv[1]
    fnames = glob.glob(os.path.join(directory, '*.json'))
    for fname in fnames:
        #print(fname)
        json_object = json.load(codecs.open(fname))
        year = int(json_object.get('year', 9999))
        if year == 9999:
            continue
        years[year] += 1
        for topic in json_object.get('topic_element', []):
            topics[topic] += 1
    json_object = { "years": years, "topics": topics }
    with codecs.open(outfile, 'w') as fh:
        fh.write(json.dumps(json_object, indent=True))


if __name__ == '__main__':

    directory = sys.argv[1]
    outfile = sys.argv[2]
    write_statistics(directory, outfile)

