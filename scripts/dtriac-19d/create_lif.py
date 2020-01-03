"""create_lif.py

Create LIF files from the Tesseract output.

Usage:

$ python create_lif.py -s SOURCE_DIR -b DATA_DIR -f FILELIST -b BEGIN -e END

The first directory is the one with files created by Tesseract, the second the
target for LIF files.

"""


import os
import sys
import getopt
import json
from io import StringIO

from lif import LIF, Container, View, Annotation
from utils import time_elapsed, elements, ensure_directory, print_element


HEADER_FILE = open("list-headers.txt", 'w')
FOOTER_FILE = open("list-footers.txt", 'w')

PAGE_NUMBERS = { '1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
                 '11', '12', '13', '14', '15', '16', '17', '18', '19', '20'}

ROMAN_NUMERALS = {'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x',
                  'xi', 'xii', 'xii', 'xiv', 'xv', 'xvi', 'xvii', 'xvii', 'xix', 'xx'}


@time_elapsed
def process_filelist(source_dir, data_dir, filelist, start, end, crash=False, test=False):
    print("$ python3 %s\n" % ' '.join(sys.argv))
    for n, fname in elements(filelist, start, end):
        print_element(n, fname)
        if crash:
            process_list_element(source_dir, data_dir, fname, test=test)
        else:
            try:
                process_list_element(source_dir, data_dir, fname, test=test)
            except Exception as e:
                print('ERROR:', Exception, e)


def process_list_element(source_dir, data_dir, fname, test=False):
    src_file = os.path.join(source_dir, fname)
    lif_file = os.path.join(data_dir, 'lif', fname[:-4] + '.lif')
    if test:
        test_lif_file(lif_file)
    else:
        ensure_directory(lif_file)
        create_lif_file(src_file, lif_file)


def create_lif_file(src_file, lif_file, test=False):
    HEADER_FILE.write("\n%s\n\n" % src_file)
    FOOTER_FILE.write("\n%s\n\n" % src_file)
    with open(src_file, encoding='utf8') as fh_in, \
         open(lif_file, 'w', encoding='utf8') as fh_out:
        lif_obj = LIF()
        page_view = create_page_view()
        lif_obj.views.append(page_view)
        text = StringIO()
        offset = 0
        page = Page(offset)
        for line in fh_in:
            if line.startswith(u"\U0001F4C3"):
                page.parse(line)
                offset = page.end
                text.write(page.text)
                anno = page.as_annotation()
                #print(anno.as_json())
                page_view.annotations.append(anno)
                page = Page(offset)
            else:
                page.add(line)
        lif_obj.text.value = text.getvalue()
        container = create_container(lif_obj)
        fh_out.write(json.dumps(container.as_json(), indent=4))
    if test:
        test_lif_file(lif_file)


def create_container(lif_object):
    container = Container()
    container.discriminator = "http://vocab.lappsgrid.org/ns/media/jsonld#lif"
    container.payload = lif_object
    return container


def create_page_view():
    view = View()
    view.id = "pages"
    view.metadata['contains'] = { vocab("Page"): {} }
    return view


class Page(object):

    def __init__(self, offset):
        self.start = offset
        self.end = None
        self.buffer = StringIO()
        self.number = None
        self.text = None
        self.header = None
        self.footer = None

    @staticmethod
    def is_header(text):
        if (text.strip('- ') in PAGE_NUMBERS
            or text.strip('- ') in ROMAN_NUMERALS):
            return True
        return False

    @staticmethod
    def is_footer(text):
        text = text.strip()
        if (text.strip('- ') in PAGE_NUMBERS
            or text.strip('- ') in ROMAN_NUMERALS):
            return True
        if len(text) <= 2 and not text.isdigit():
            return True
        return False

    def add(self, line):
        self.buffer.write(line)

    def parse(self, line):
        self.number = line.strip().strip(u"\U0001F4C3").strip()
        self.text = self.buffer.getvalue()
        self.split_header()
        self.split_footer()
        self.end = self.start + len(self.text)

    def split_header(self):
        header_and_text = self.text.split("\n\n", 1)
        if len(header_and_text) == 2:
            header, text = header_and_text
            # Candidate headers are one line only.
            if header.find('\n') == -1:
                if self.is_header(header):
                    #print('H', header)
                    self.text = text
                    self.header = header.strip()
                    HEADER_FILE.write("+ %s\n" % header)
                else:
                    HEADER_FILE.write("- %s\n" % header)

    def split_footer(self):
        text_and_footer = self.text.strip().rsplit("\n\n", 1)
        if len(text_and_footer) == 2:
            text, footer = text_and_footer
            # Candidate footers are one line only.
            if footer.find('\n') == -1:
                if self.is_footer(footer):
                    #print('F', footer)
                    self.text = text
                    self.footer = footer.strip()
                    FOOTER_FILE.write("+ %s\n" % footer)
                else:
                    FOOTER_FILE.write("- %s\n" % footer)

    def as_annotation(self):
        properties = {
            "id": "p%s" % self.number,
            "@type": vocab('Page'),
            "start": self.start,
            "end": self.end,
            "features": {} }
        if self.header is not None:
            properties['features']['header'] = self.header
        if self.footer is not None:
            properties['features']['footer'] = self.footer
        return Annotation(properties)


def test_lif_file(lif_file):
    """Just print the text of all headers, should give an indication of whether all
    the offsets are correct."""
    lif = Container(json_file=lif_file).payload
    text = lif.text.value
    view = lif.views[0]
    for anno in view.annotations:
        page = text[anno.start:anno.end]
        print("<{}> {}".format(anno.id, ' '.join(page[:80].split())))
    print('')


def vocab(annotation_type):
    return "http://vocab.lappsgrid.org/{}".format(annotation_type)


if __name__ == '__main__':

    data_dir = '/DATA/dtra/dtriac/dtriac-19d/dtriac-19d-00100'
    filelist = 'files-random.txt'

    options = dict(getopt.getopt(sys.argv[1:], 's:d:f:b:e:h', ['test', 'crash', 'help'])[0])
    source_dir = options.get('-s', data_dir)
    data_dir = options.get('-d', data_dir)
    filelist = options.get('-f', filelist)
    start = int(options.get('-b', 1))
    end = int(options.get('-e', 1))
    crash = True if '--crash' in options else False
    test = True if '--test' in options else False
    help_wanted = True if '-h' in options or '--help' in options else False

    if help_wanted:
        usage()
    else:
        print(source_dir, data_dir, filelist, start, end, crash, test)
        process_filelist(source_dir, data_dir, filelist, start, end, crash=crash, test=test)
