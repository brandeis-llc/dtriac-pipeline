"""check.py

Perform sanity checks on a directory with LIF files. 

Usage:

$ python check.py DIRECTORY ANNOTATION_TYPE LIMIT?

Loads the LIF files in DIRECTORY and for each of them prints the text strings of
all annotations of type TANNOTATION_TYPE. The optional LIMIT argument limits how
many files are checked.

For example:

$ python check.py samples/sample-25-ttk TimeExpression 3

The output will have lines like

   TimeExpression  20 February 2018
   TimeExpression  25 April 2018

and it should be easy to see if something is wrong.

"""

import os
import sys
from lif import LIF, Container


def check_files(folder, tagname, limit=999):
    c = 0
    for fname in os.listdir(folder):
        c += 1
        if c > limit:
            break
        fpath = os.path.join(folder, fname)
        if os.path.isfile(fpath):
            check_file(fpath, tagname)

    
def check_file(fpath, tagname):
    print("\n{}\n".format(fpath))
    lif = get_lif(fpath)
    text = lif.text.value
    for view in lif.views:
        for anno in view.annotations:
            if anno.type.endswith(tagname):
                print("   {}  {}-{}  {}".format(tagname, anno.start, anno.end, grab_text(text, anno)))


def get_lif(fpath):
    try:
        lif = Container(fpath).payload
    except:
        lif = LIF(fpath)
    return lif

                    
def grab_text(text, anno):
    return text[anno.start:anno.end][:80].replace('\n', ' ')


if __name__ == '__main__':
    
    folder = sys.argv[1]
    tagname = sys.argv[2]
    limit = 999
    if len(sys.argv) > 3:
        limit = int(sys.argv[3])
    check_files(folder, tagname, limit)
