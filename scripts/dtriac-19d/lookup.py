"""lookup.py

Uses two data files
- technologies.txt
- technologies-stoplist.txt

The first is created by compile_technologies(), which runs on the output of the
Techknowledgist classifier code. The second was at some point created from the
first by selecting the 2000+ most frequent technologies listed on descending
frequency (those occurring 10 times or more) and then manually annotating the
lines that are not technology terms. As of Jan 7th 2020 the first 300 lines were
annotated.

You can get the value for LONGUEST_TECHNOLOGY by running longest_technology().

"""

import os
import sys
from collections import Counter

from lif import Container, LIF, View, Annotation
from utils import get_options, process_list, ensure_directory, create_view


DEBUG = False

TECHNOLOGY_LIST = 'technologies.txt'
TECHNOLOGY_STOPLIST = 'technologies-stoplist.txt'
TECHNOLOGIES = None

LONGEST_TECHNOLOGY = 7

SCORES_FILE = 'classify.MaxEnt.out.s4.scores.sum.az'

MIN_SCORE = 0.5
MIN_COUNT = 5


if DEBUG:
    OUT = open('lists/list-technologies-found.txt', 'w')


def compile_technologies(classification, technologies_file):
    """Create a list of technologies from the output of the technology
    classifier. Include only the terms with a score of at least MIN_SCORE and a
    frequency of at least MIN_COUNT. Save tab-separated tuples with count, score
    and term."""
    classification_file = os.path.join(classification, SCORES_FILE)
    with open(classification_file) as fh_in, \
         open(technologies_file, 'w') as fh_out:
        for line in fh_in:
            if line[0] in ' \t\n':
                continue
            term, score, count, low, high = line.strip().split('\t')
            score = float(score)
            count = int(count)
            if score >= MIN_SCORE and count >= MIN_COUNT:
                fh_out.write("%d\t%f\t%s\n" % (count, score, term))


def lookup_technologies(data_dir, fname):

    subdir = os.path.split(fname)[0]
    pos_file = os.path.join(data_dir, 'pos', subdir, "%s.ner.lif" % subdir)
    tex_file = os.path.join(data_dir, 'tex', subdir, "%s.lup.lif" % subdir)
    ensure_directory(tex_file)
    lif = Container(pos_file).payload
    lif_tex = LIF(json_object=lif.as_json())
    pos_view = lif.get_view('v2')
    tex_view = create_view('tex', 'Technology', 'dtriac-pipeline:lookup.py')
    lif_tex.views = [tex_view]

    tokens = [a for a in pos_view.annotations if a.type.endswith('Token')]
    next_id = 0
    for i in range(len(tokens)):
        pairs = [(get_text_from_tokens(tokens, i, i + j), j) for j in range(2,8)]
        for w, length in pairs:
            if w in TECHNOLOGIES.terms:
                p1 = tokens[i].start
                p2 = tokens[i+length].end
                OUT.write("%s\t%s\t%s\n" % (p1, p2, w))
                #print(p1, p2, w)

                next_id += 1
                json_obj = { "id": "t%d" % next_id,
                             "@type": 'http://vocab.lappsgrid.org/Technology',
                             "start": p1, "end": p2,
                             "features": { "term": w }}
                anno = Annotation(json_obj)
                tex_view.annotations.append(anno)

    lif_tex.write(fname=tex_file, pretty=True)


def longest_technology():
    lengths = [len(t.split()) for t in TECHNOLOGIES.terms]
    c = Counter(lengths)
    print(c)
    longest = 0
    for t in TECHNOLOGIES.terms:
        tokens = t.split()
        longest = max(longest, len(tokens))
    return longest


def get_text_from_tokens(tokens, p1, p2):
    return ' '.join([t.features.get('word') for t in tokens[p1:p2]])


class TechnologyOntology(object):

    """TechnologyOntology is rather a big word for this since all this does at the
    moment is to keep a list of technologies and a stoplist of terms that are not
    technologies."""

    def __init__(self):
        self.terms = set()
        self.stoplist = set()
        for line in open(TECHNOLOGY_STOPLIST):
            if line.startswith('- '):
                self.stoplist.add(line.strip()[2:])
        for line in open(TECHNOLOGY_LIST):
            count, score, term = line.strip().split('\t')
            if not self.filter(term) and not term in self.stoplist:
                self.terms.add(term)

    def __len__(self):
        return len(self.terms)

    def __str__(self):
        return "<TechnologyOntology terms=%d>" % len(self)

    def filter(self, term):
        if (term[0] in '!%-\\©®°'
            or term.startswith('appendices')
            or term.startswith('figures')
            or term.startswith('c/o')
            or term.startswith('cents')
            or term.startswith('c0 ')
            or term.startswith('d ')
            or term.startswith('d. ')
            or len(term) > 50):
            return True
        return False


if __name__ == '__main__':

    if sys.argv[1] == "--compile-technologies":
        classification = sys.argv[2]
        compile_technologies(classification, 'technologies.txt')
    else:
        data_dir, filelist, start, end, crash = get_options()
        TECHNOLOGIES = TechnologyOntology()
        # print("Loaded %s" % TECHNOLOGIES)
        print(longest_technology())
        process_list(data_dir, filelist, start, end, crash, lookup_technologies)

