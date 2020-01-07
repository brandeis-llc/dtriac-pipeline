"""generate_sentence_type.py

Script that uses a few very simple heuristics to determine whether a sentence is
normal or crap. In order to be considered normal a sentence should exhibit the
following characteristics:

- minimum number of tokens is 4
- minimum number of charaters is 20
- minimum ratio of known words is 0.55

Uses NLTK's words list, tokenizer and lemmatizer. Initializing those takes some
time while processing the first file (about 3-5 seconds on a 2015 3.2GHz iMac).

Usage:

$ python generate_sentence_type.py -d DATA_DIR

This collects information from DATA_DIR/lif and DATA_DIR/spl and writes to
DATA_DIR/sen.

If DEBUG is set to True aggregate results will be written to sents-good.txt and
sents-bad.txt for inspection.

"""


import os, sys, codecs

from nltk.corpus import words
from nltk import word_tokenize
from nltk.stem import WordNetLemmatizer

from lif import Container, LIF, View
from utils import get_options, process_list, ensure_directory


DEBUG = False
DEBUG = True

MINIMUM_NUMBER_OF_TOKENS = 4
MINIMUM_NUMBER_OF_CHARACTERS = 20
MINIMUM_RATIO_OF_KNOWN_WORDS = 0.55


LEMMATIZER = WordNetLemmatizer()
WORDS = set(words.words())
print("Loaded %s words\n" % len(WORDS))

if DEBUG:
    SENTS = codecs.open('sentences.txt', 'w', encoding='utf8')


def generate_sentence_types(data_dir, fname):

    subdir = os.path.split(fname)[0]
    lif_file = os.path.join(data_dir, 'lif', subdir, "tesseract-300dpi-20p.lif")
    spl_file = os.path.join(data_dir, 'spl', subdir, "%s.ner.lif" % subdir)
    sen_file = os.path.join(data_dir, 'sen', subdir, "%s.sen.lif" % subdir)
    ensure_directory(sen_file)

    if DEBUG:
        SENTS.write(">>> %s\n>>> %s\n>>> %s\n\n" % ('-' * 100, fname, '-' * 100))

    lif = Container(lif_file).payload
    lif_spl = Container(spl_file).payload
    lif_sen = LIF(json_object=lif.as_json())

    spl_sentences_view = lif_spl.get_view('v2')
    new_sentences_view = _create_view()
    lif_sen.views = [new_sentences_view]

    good_sentences = 0
    bad_sentences = 0

    for anno in spl_sentences_view.annotations:
        if anno.type.endswith('Sentence'):
            sc = SentenceClassifier(lif, anno, WORDS)
            if sc.is_crap():
                if DEBUG:
                    SENTS.write("---- %f\n%s\n\n" % (sc.ratio, repr(sc.text)))
                anno.features['type'] = 'crap'
                bad_sentences += 1
            else:
                if DEBUG:
                    SENTS.write("++++ %f\n%s\n\n" % (sc.ratio, repr(sc.text)))
                anno.features['type'] = 'normal'
                good_sentences += 1
            new_sentences_view.annotations.append(anno)
    if DEBUG:
        SENTS.write("\nTOTAL GOOD = {:d}\nTOTAL BAD  = {:d}\n\n\n".format(good_sentences, bad_sentences))

    lif_sen.write(fname=sen_file, pretty=True)


def _create_view():
    view_spec = {
        'id': "sentences",
        'metadata': {
            'contains': {
                'http://vocab.lappsgrid.org/Sentence': {
                    'producer': 'generate_sentence_type.py'}}},
        'annotations': []}
    return View(json_obj=view_spec)


class SentenceClassifier(object):

    def __init__(self, lif, annotation, words):
        self.words = words
        self.annotation = annotation
        self.text = lif.text.value[annotation.start:annotation.end]
        self.tokens = [t.lower() for t in word_tokenize(self.text)]
        self.length = len(self.tokens)
        self.common = len([t for t in self.tokens if LEMMATIZER.lemmatize(t) in WORDS])
        try:
            self.ratio = float(self.common) / self.length
        except ZeroDivisionError:
            self.ratio = 0

    def is_crap(self):
        return self.length < MINIMUM_NUMBER_OF_TOKENS \
            or len(self.text) < MINIMUM_NUMBER_OF_CHARACTERS \
            or self.ratio < MINIMUM_RATIO_OF_KNOWN_WORDS


if __name__ == '__main__':

    data_dir, filelist, start, end, crash = get_options()
    process_list(data_dir, filelist, start, end, crash, generate_sentence_types)
