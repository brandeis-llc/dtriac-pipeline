"""get_random_dtriac_19d_data.py

Get a sample from the dtriac-19d data.

Usage:

$ python3 get_random_dtriac_19d_data.py N OUTDIR

Take N files from FILELIST and save them to OUTDIR.

FILELIST was created by

$ find /data/dtriac/dtriac-19d/all | grep tesseract- > files-sorted-tesseract.txt
$ sort -R files-sorted-tesseract.txt > files-random-tesseract.txt 

"""

import os, sys, shutil

FILELIST = 'files-random-tesseract.txt'


def create_sample(end, outdir):
    count = 0
    for line in open(FILELIST):
        count += 1
        fname = line.strip()
        path1, basename = os.path.split(fname)
        path2, directory = os.path.split(path1)
        print('%04d  %6s  %s' % (count, directory, basename))
        target = os.path.join(outdir, directory, basename)
        ensure_directory(target)
        shutil.copyfile(fname, target)
        if count >= end:
            break


def ensure_directory(*fnames):
    """Ensure the directory part of all file names exists."""
    for fname in fnames:
        directory = os.path.split(fname)[0]
        if not os.path.exists(directory):
            os.makedirs(directory)


if __name__ == '__main__':

    end = int(sys.argv[1])
    outdir = sys.argv[2]
    
    create_sample(end, outdir)
