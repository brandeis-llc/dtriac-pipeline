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
    page_separator = '\n\n%s\n\n' % ('='*80)
    page_separator = ''
    with open(src_file, encoding='utf8') as fh_in, \
         open(lif_file, 'w', encoding='utf8') as fh_out:
        lif_obj = LIF()
        _add_view(lif_obj)
        annotations = lif_obj.views[0].annotations
        text = StringIO()
        page_start = 0
        page_end = 0
        offset = 0
        for line in fh_in:
            if line.startswith(u"\U0001F4C3"):
                page_number = line.strip().strip(u"\U0001F4C3").strip()
                #print(line.strip(), '  -- ', page_number, page_start, page_end)
                offset += text.write(page_separator)
                _add_annotation(annotations, 'Section', page_number, page_start, page_end)
                page_start = offset
                page_end = offset
            else:
                sent_len = text.write(line)
                page_end += sent_len
                offset += sent_len
        lif_obj.text.value = text.getvalue()
        container = Container()
        container.discriminator = "http://vocab.lappsgrid.org/ns/media/jsonld#lif"
        container.payload = lif_obj
        fh_out.write(json.dumps(container.as_json(), indent=4))
    if test:
        test_lif_file(lif_file)


def _add_view(lif_obj):
    view = View()
    lif_obj.views.append(view)
    view.id = "structure"
    view.metadata['contains'] = { vocab("Section"): {} }


def _add_annotation(annotations, annotation_type, page_number, start, end):
    anno = {
        "id": "p%s" % page_number,
        "@type": vocab('Section'),
        "start": start,
        "end": end }
    annotations.append(Annotation(anno))


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
        process_filelist(source_dir, data_dir, filelist, start, end, crash=crash, test=test)
