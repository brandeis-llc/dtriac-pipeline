"""show_annotations.py

Code to check whether created LIF files make sense. Takes files in DIRECTORY,
orders them randomly, and then prints the text of all instances of TAG to the
output.

$ python3 show_annotations.py TAG DIRECTORY

For example:

$ python3 show_annotations.py Sentence /DATA/dtra/dtriac-19d-00100-processed/spl

"""

import os
import sys
import random
import re

from lif import Container


RED = '\u001b[31m'
BLUE = '\u001b[34;1m'
GREEN = '\u001b[32;1m'
REV = '\u001b[7m'
END = '\u001b[0m'

WIDTH = 100


def show(tag, path):
    dirs = os.listdir(path)
    random.shuffle(dirs)
    tag = "http://vocab.lappsgrid.org/%s" % tag
    for d in dirs:
        show_file(tag, path, d)
        show_next = input("\nNext? (y/n): ")
        if show_next == 'n':
            break


def show_file(tag, path, subdir):
    data_dir = os.path.join(path, subdir)
    files = [f for f in os.listdir(data_dir) if f[0].isdigit()]
    if len(files) != 1:
        print('Unexpected directory contents')
        return
    data_file = os.path.join(data_dir, files[0])
    print("\n%s%s/%s%s" % (BLUE, subdir, os.path.basename(data_file), END))
    lif = Container(json_file=data_file).payload
    count = 0
    print()
    for view in lif.views:
        for anno in view.annotations:
            if anno.type == tag:
                p1, p2 = anno.start, anno.end
                text = lif.text.value[p1:p2]
                if tag.endswith('Sentence'):
                    print("%s" % ('>' * WIDTH))
                    print(lif.text.value[p1:p2])
                    input()
                else:
                    category = anno.features.get('category')
                    if category in ('number', 'ordinal', 'percent', 'money', 'misc'):
                        continue
                    if category is not None:
                        category = '%-20s' % (category + ':')
                    else:
                        category = ''
                    left = "%-25s" % lif.text.value[p1-25:p1]
                    right = lif.text.value[p2:p2+25]
                    context = "%s%s%s %s %s%s" % (category, left, BLUE, text, END, right)
                    context = context.replace('\n', ' ')
                    print(context, end='\n')
                    count += 1
                    if count % 25 == 0:
                        input()


if __name__ == '__main__':

    tag = sys.argv[1]
    path = sys.argv[2]
    show(tag, path)
