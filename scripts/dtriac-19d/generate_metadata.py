"""generate_metadata.py

Adding year and authors to metadata field.

Usage:

$ python generate_metadata.py -d DATA_DIR -f FILELIST -s START -e END

Uses data in DATA_DIR/lif an DATA_DIR/ner and generates data in DATA_DIR/mta.

TODO:

Now we take all names, after some filtering from the window. Do two things:
- look for names page by page
- filter for things like John Doe Director
- split on new line
- get rid of duplicates

Add month abbreviations to MONTHS

"""

import os
import re

from lif import Container, LIF, View
from utils import get_options, process_list, ensure_directory


# two settings that determine where we look for metadata
METADATA_PAGES = 5
METADATA_WINDOW_MAXIMUM = 10000

EARLIEST_DOC = 1950
LATEST_DOC = 2020

MONTHS = { 'january', 'february', 'march', 'april', 'may', 'june',
           'july', 'august', 'september', 'october', 'november', 'december' }

# Common first names and set of names to be filtered
# TODO: this is copied from create_index_docs.py, refactor this
FIRST_NAMES = 'data/names/common-first-names.txt'
NAMES_TO_FILTER = set()


def generate_metadata(data_dir, fname):

    subdir = os.path.split(fname)[0]
    lif_file = os.path.join(data_dir, 'lif', subdir, "tesseract-300dpi-20p.lif")
    ner_file = os.path.join(data_dir, 'ner', subdir, "%s.ner.lif" % subdir)
    mta_file = os.path.join(data_dir, 'mta', subdir, "%s.mta.lif" % subdir)
    ensure_directory(mta_file)

    lif = Container(lif_file).payload
    lif_ner = Container(ner_file).payload
    lif_mta = LIF(json_object=lif.as_json())
    lif_mta.text.value = None
    lif_mta.text.fname = lif_file
    lif_mta.views = []
    lif.metadata["authors"] = []
    lif.metadata["year"] = None

    page_view = lif.get_view("pages")
    ner_view = lif_ner.get_view('v2')

    window = _get_window(page_view)
    lif.metadata["authors"] = _get_authors(ner_view, window)
    lif.metadata["year"] = _get_year(ner_view, window)

    lif_mta.write(fname=mta_file, pretty=True)


def _get_window(page_view):
    """Get the offset window in which we will be looking for metadata. This is
    window is from offset 0 to lesser of a) the last offset of the last page
    considered for metadata and b) a preset maximum offset."""
    return (0, min(METADATA_WINDOW_MAXIMUM, page_view.annotations[METADATA_PAGES].end))


def _get_authors(ner_view, window):
    authors = []
    for anno in ner_view.annotations:
        if anno.features.get('category') == 'person':
            if anno.end <= window[1]:
                authors.append(anno.features['word'])
    authors = [a for a in authors if ' ' in a]
    #length1 = len(authors)
    authors = [a for a in authors if not filter_name(a)]
    #length2 = len(authors)
    #if length2 < length1:
    #    print(length1, length2)
    #print('   ', authors)
    return authors


def _get_year(ner_view, window):
    dates = []
    for anno in ner_view.annotations:
        if anno.features.get('category') == 'date':
            if anno.end <= window[1]:
                dates.append(anno.features['word'])
    dates = [d for d in dates if is_nice_date(d)]
    #print('   ', dates)
    if dates:
        years = [get_year(d) for d in dates]
        for year in years:
            if EARLIEST_DOC < year  < LATEST_DOC:
                #print('   ', year)
                return year
    return None


def is_nice_date(date):
    """Something is a nice date if it has a month in it."""
    for t in date.split():
        if t.lower() in MONTHS:
            return True
    return False


def get_year(date):
    for t in date.split():
        if t.isdigit() and len(t) == 4:
            return int(t)
    return 0


def filter_name(name):
    # remove some names: common first names, Jr and Sr
    if (name.lower() in NAMES_TO_FILTER
        or name in ('Jr', 'Jr.', 'Sr', 'Sr.')):
        return True
    # Roads tend to be recognized as names, we don't like that
    if name.endswith(' Road'):
        return True
    return False


def load_first_names():
    # TODO: copied from create_index_docs.py, refactor this
    for line in open(FIRST_NAMES):
        if line.startswith('#'):
            continue
        (rank, male, count1, female, count2) = line.strip().split('\t')
        NAMES_TO_FILTER.add(male.lower())
        NAMES_TO_FILTER.add(female.lower())


if __name__ == '__main__':

    data_dir, filelist, start, end, crash = get_options()
    load_first_names()
    process_list(data_dir, filelist, start, end, crash, generate_metadata)
