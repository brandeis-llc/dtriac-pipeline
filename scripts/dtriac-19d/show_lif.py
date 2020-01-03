"""show_lif.py

Code to check whether created LIF files make sense. Writes output with the OCR
result and the LIF created from that and prints it together for easy eyeballing.

$ python3 show_lif.py
    /DATA/dtra/dtriac/dtriac-19d/dtriac-19d-00100
    /DATA/dtra/dtriac/dtriac-19d/dtriac-19d-00100-processed/lif

"""

import os
import sys
import random
import re

from lif import Container


# Set this to True if you only want to see pages that have a header or footer
HEADERS_FOOTERS_ONLY = False


RED = '\u001b[31m'
BLUE = '\u001b[34;1m'
GREEN = '\u001b[32;1m'
REV = '\u001b[7m'
END = '\u001b[0m'

WIDTH = 80

PAGE_MARKER = u"\n\U0001F4C3 00\d\d \U0001F4C3\n"


def show(sourcepath, datapath):
    dirs = os.listdir(datapath)
    random.shuffle(dirs)
    for d in dirs:
        show_file(sourcepath, datapath, d)
        show_next = input("\nNext? (y/n): ")
        if show_next == 'n':
            break


def show_file(sourcepath, datapath, subdir):
    sourcefile = os.path.join(sourcepath, subdir, 'tesseract-300dpi-20p.txt')
    datafile = os.path.join(datapath, subdir, 'tesseract-300dpi-20p.lif')
    print("\n%s%s/%s%s" % (BLUE, subdir, os.path.basename(datafile), END))
    lif = Container(json_file=datafile).payload
    annotations = lif.views[0].annotations
    pages = get_pages(sourcefile)
    if len(pages) != len(annotations):
        print("WARNING: unequal number of pages and page annotations (%d != %d)"
              % (len(pages), len(annotations)))
    for page, annotation in zip(pages, annotations):
        if (HEADERS_FOOTERS_ONLY
            and annotation.features.get('header') is None
            and annotation.features.get('footer') is None):
            continue
        print_annotation(annotation)
        print_page(page)
        print_page(lif.text.value[annotation.start:annotation.end])
        input()


def get_pages(sourcefile):
    content = open(sourcefile).read()
    pages = [p.strip() for p in re.split(PAGE_MARKER, content)][:-1]
    return pages


def print_annotation(annotation):
    header = annotation.features.get('header', '')
    footer = annotation.features.get('footer', '')
    print("\n%s%s  [%s]  [%s] %s" % (GREEN, annotation.id, header, footer, END))


def print_page(page):
    print('\n%s' % ('>' * WIDTH))
    print_first_lines(page)
    print('%s' % ('=' * WIDTH))
    print_last_lines(page)
    print('%s\n' % ('<' * WIDTH))


def print_first_lines(text, n=5):
    lines = text.split('\n')
    i = 0
    for line in lines[:n]:
        i += 1
        print("%d:  %s" % (i, line))


def print_last_lines(text, n=5):
    lines = text.split('\n')
    i = 0
    for line in lines[-n:]:
        i += 1
        print("%d:  %s" % (i, line))




if __name__ == '__main__':

    sourcepath = sys.argv[1]
    datapath = sys.argv[2]
    show(sourcepath, datapath)
