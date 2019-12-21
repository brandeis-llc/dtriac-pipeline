"""run_tarsqi.py

Use Python 2.7 for this.

Also need something like

$ export PYTHONPATH=/users/marc/tools/ttk

Practice run on first 1000 documents:
- runtime: 415 seconds
- data size: 151M
Translated to 2M documents:
- runtime: 240 hours
- data size: 315G

Saving files as gz files reduces diskspace use by a factor 15 with no difference
in processing time.

"""


import os
import sys
import getopt
import gzip

import tarsqi
from utilities import lif

from utils import time_elapsed, elements, ensure_directory, print_element
from lif import Container


COMPRESS = True


@time_elapsed
def run_tarsqi(data_dir, filelist, start, end, crash=False):
    print("$ python3 %s" % ' '.join(sys.argv))
    for n, fname in elements(filelist, start, end):
        print_element(n, fname)
        if crash:
            run_tarsqi_for_file(data_dir, fname)
        else:
            try:
                run_tarsqi_for_file(data_dir, fname)
            except Exception as e:
                print('ERROR:', Exception, e)


def run_tarsqi_for_file(data_dir, fname):
    lif_file = os.path.join(data_dir, 'lif', fname[:-4] + '.lif')
    ttk_file = os.path.join(data_dir, 'ttk', fname[:-4] + '.lif')
    ensure_directory(ttk_file)
    lif = Container(lif_file).payload
    text = lif.text.value
    doc = parse_text(text)
    if COMPRESS:
        with gzip.open(ttk_file + '.gz', 'wb') as fh:
            doc.print_all_lif(fh)
    else:
        with open(ttk_file, 'w') as out:
            doc.print_all_lif(out)


def parse_text(text):
    doc = tarsqi.process_string(text, pipeline='PREPROCESSOR,EVITA,GUTIME')
    doc.sourcedoc.lif = lif.LIF(json_object={"text": { "@value": text}, "views": []})
    doc.sourcedoc.lif.add_tarsqi_view(doc)
    purge_metadata(doc.sourcedoc.lif.views[0].metadata)
    return doc


def purge_metadata(metadata):
    for key in ["http://vocab.lappsgrid.org/TemporalRelation"]:
        metadata['contains'].pop(key, None)


def usage():
    pass


if __name__ == '__main__':

    #doc = parse_text("We walked home on Monday")
    #doc.print_all_lif(sys.stdout)

    data_dir = '/DATA/eager/sample-01000'
    filelist = '../../data/files-random-01000.txt'

    options = dict(getopt.getopt(sys.argv[1:], 'd:f:s:e:h', ['crash', 'help'])[0])
    data_dir = options.get('-d', data_dir)
    filelist = options.get('-f', filelist)
    start = int(options.get('-s', 1))
    end = int(options.get('-e', 1))
    crash = True if '--crash' in options else False
    help_wanted = True if '-h' in options or '--help' in options else False

    if help_wanted:
        usage()
    else:
        run_tarsqi(data_dir, filelist, start, end, crash=crash)

