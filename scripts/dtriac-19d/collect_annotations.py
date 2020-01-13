"""collect_annotations.py

Code to collect annotations of a particular kind. Takes some number of files in
DIRECTORY and then prints the text of all instances of TAG to standard output,
using the feat-value pair if one was given.

$ python3 collect_annotations.py DIRECTORY N TAG (feat=val)

For example:

$ export DATA=/DATA/dtra/dtriac-19d-00100-processed/
$ python3 show_annotations.py $DATA/ner 100 NamedEntity category=location

"""

import os
import sys
from collections import Counter

from lif import Container


def collect(path, n, tag, restriction=None):
    print("# SCRIPT  =  %s" % 'scripts/dtriac-19d/collect_annotations.py')
    print("# PATH    =  %s" % path)
    print("# FILES   =  %s" % n)
    print("# TAG     =  %s" % tag)
    feat, val = None, None
    if restriction is not None:
        feat, val = restriction.split('=')
        print("# FEAT    =  %s=%s" % (feat, val))
    full_tag = "http://vocab.lappsgrid.org/%s" % tag
    processing_step = os.path.split(path)[1]
    subdirs = os.listdir(path)[:int(n)]
    locations = []
    for subdir in subdirs:
        fname = os.path.join(path, subdir, "%s.%s.lif" % (subdir, processing_step))
        lif = Container(fname).payload
        for view in lif.views:
            for annotation in view.annotations:
                if annotation_matches(annotation, full_tag, feat, val):
                    p1 = annotation.start
                    p2 = annotation.end
                    locations.append(annotation.features.get('word'))
    locs = Counter(locations)
    total_count = sum(locs.values())
    print("# HITS    =  %d" % total_count)
    for loc, count in locs.most_common():
        print("%d \t%s" % (count, loc))


def annotation_matches(annotation, tagname, feat, val):
    if annotation.type != tagname:
        return False
    if feat is not None:
        return annotation.features.get(feat) == val
    else:
        return True


if __name__ == '__main__':

    path = sys.argv[1]
    count = sys.argv[2]
    tag = sys.argv[3]
    restriction = sys.argv[4] if len(sys.argv) > 4 else None
    collect(path, count, tag, restriction)
