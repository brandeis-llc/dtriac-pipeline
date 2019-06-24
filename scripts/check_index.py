"""check_index.py

Checks the index files to see if something is fishy. Now just checks all the
events and if one starts or ends with a space then probably something went wrong
with offsets.

Usage:

$ python check_index.py DIRECTORY

The directory is the ELA directory.

Prints names of files that seem wrong to standard output.

This identified 13 files with offset issues.

"""


import os, sys, glob, json, codecs



def check_directory(index_directory):
    fnames = glob.glob(os.path.join(index_directory, '*.json'))
    for fname in fnames:
        check_file(fname)

def check_file(fname):
    #print fname
    json_object = json.load(codecs.open(fname))
    for event in json_object['event']:
        if event.startswith(' ') or event.endswith(' '):
            print fname
            return
        if event and event[-1] in (',', '.'):
            print fname
            return


if __name__ == '__main__':

    index_directory = sys.argv[1]
    check_directory(index_directory)
