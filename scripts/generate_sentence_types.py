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

$ python generate_sentence_type.py TTK_DIR OUT_DIR

This processes all files in TTK_DIR and writes to OUT_DIR.

If DEBUG is set to True aggregate results will be written to sents-good.txt and
sents-bad.txt for inspection.

"""

import os, sys, codecs

from nltk.corpus import words
from nltk import word_tokenize
from nltk.stem import WordNetLemmatizer

from lif import LIF, View


DEBUG = False

MINIMUM_NUMBER_OF_TOKENS = 4
MINIMUM_NUMBER_OF_CHARACTERS = 20
MINIMUM_RATIO_OF_KNOWN_WORDS = 0.55


LEMMATIZER = WordNetLemmatizer()
WORDS = set(words.words())
print("Loaded %s words\n" % len(WORDS))

if DEBUG:
    GOOD = codecs.open('sents-good.txt', 'w', encoding='utf8')
    BAD = codecs.open('sents-bad.txt', 'w', encoding='utf8')


def generate_sentence_types(ttk, sen, words):
    for fname in os.listdir(ttk):
        print("{} ... ".format(os.path.basename(fname)), end=' ')
        if DEBUG:
            GOOD.write(">>> %s\n>>> %s\n>>> %s\n\n" % ('-' * 100, fname, '-' * 100))
            BAD.write(">>> %s\n>>> %s\n>>> %s\n\n" % ('-' * 100, fname, '-' * 100))
        fname_in = os.path.join(ttk, fname)
        fname_out = os.path.join(sen, fname)
        lif_in = LIF(fname_in)
        lif_out = LIF(json_object=lif_in.as_json())
        sentences_view = _create_view()
        lif_out.views = [sentences_view]
        good_sentences = 0
        bad_sentences = 0
        view = lif_in.get_view('v1')
        for anno in view.annotations:
            if anno.type.endswith('Sentence'):
                sc = SentenceClassifier(lif_in, anno, words)
                if sc.is_crap():
                    if DEBUG:
                        BAD.write(">>> %f\n%s\n\n" % (sc.ratio, sc.text))
                    anno.features['type'] = 'crap'
                    bad_sentences += 1
                else:
                    if DEBUG:
                        GOOD.write(">>> %f\n%s\n\n" % (sc.ratio, sc.text))
                    anno.features['type'] = 'normal'
                    good_sentences += 1
                sentences_view.annotations.append(anno)
        print(" (good={:d} bad={:d})".format(good_sentences, bad_sentences))
        lif_out.write(fname=fname_out, pretty=True)
        #break
    print


def _create_view():
    view_spec = {
        'id': "Sentences",
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
        self.ratio = float(self.common) / self.length

    def is_crap(self):
        return self.length < MINIMUM_NUMBER_OF_TOKENS \
            or len(self.text) < MINIMUM_NUMBER_OF_CHARACTERS \
            or self.ratio < MINIMUM_RATIO_OF_KNOWN_WORDS


if __name__ == '__main__':
    
    ttk, sen = sys.argv[1:3]
    generate_sentence_types(ttk, sen, words)
