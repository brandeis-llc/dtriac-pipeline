"""generate_topics.py

Usage:

$ python generate_topics.py LIF_DIR OUT_DIR

This processes all files in LIF_DIR and writes to OUT_DIR.

"""

# TODO: give model building a separate flag
# TODO: add topic model directory as a parameter
# TODO: code now assumes that ../topics exists
# TODO: code also assumes that OUT_DIR exists


import os
import sys
import codecs
import pickle

import gensim
from gensim import corpora

import nltk
from nltk import word_tokenize
from nltk import sent_tokenize
from nltk.corpus import wordnet as wn

from lif import Container, LIF, View, Annotation


DATA_DIR = "../topics"
CORPUS_FILE = os.path.join(DATA_DIR, 'corpus.pkl')
DICTIONARY_FILE = os.path.join(DATA_DIR, 'dictionary.gensim')
MODEL_FILE = os.path.join(DATA_DIR, 'model5.gensim')

NUM_TOPICS = 100

STOPWORDS = set(nltk.corpus.stopwords.words('english'))


def build_model(lif_dir):

    print("\nCollecting data")
    text_data = _collect_data(lif_dir)

    print("\nLoading text data into dictionary")
    dictionary = corpora.Dictionary(text_data)

    print("\nCreating bag-of-words corpus")
    corpus = [dictionary.doc2bow(text) for text in text_data]

    print("\nCreating LDA model")
    ldamodel = gensim.models.ldamodel.LdaModel(corpus, num_topics=NUM_TOPICS,
                                               id2word=dictionary, passes=15)

    print("\nSaving dictionary, corpus and LDA model to disk\n")
    pickle.dump(corpus, open(CORPUS_FILE, 'wb'))
    dictionary.save(DICTIONARY_FILE)
    ldamodel.save(MODEL_FILE)


def _collect_data(lif_dir):
    all_data = []
    for fname in os.listdir(lif_dir):
        print("  {}".format(os.path.basename(fname)))
        fpath = os.path.join(lif_dir, fname)
        lif = Container(fpath).payload
        text_data = prepare_text_for_lda(lif.text.value)
        all_data.append(text_data)
        if fname.startswith('888'):
            break
    print('')
    print(len(text_data), 'sentences')
    print(sum([len(s) for s in text_data]), 'tokens')
    return all_data


def print_model(lda=None):
    if lda is None:
        lda = load_model()
    topics = lda.print_topics(num_words=5)
    print('\nTop 20 topics of total {:d} topics:\n'.format(len(lda.get_topics())))
    for topic in topics:
        print('  ', topic)


def load_model():
    return gensim.models.ldamodel.LdaModel.load(MODEL_FILE)


def load_dictionary():
    return corpora.Dictionary.load(DICTIONARY_FILE)


def generate_topics(lif, top):

    lda = load_model()
    topic_idx = {topic_id: topic for topic_id, topic
                 in lda.print_topics(num_topics=NUM_TOPICS)}
    dictionary = load_dictionary()

    for fname in os.listdir(lif):

        if not fname.endswith('.lif'):
            continue
        # if not fname.startswith('z'): continue

        topic_id = 0
        print("{}".format(os.path.basename(fname)))
        fname_in = os.path.join(lif, fname)
        fname_out = os.path.join(top, fname)
        lif_in = Container(fname_in).payload
        lif_out = LIF(json_object=lif_in.as_json())
        # just to save some space, we get them from the lif file anyway
        lif_out.metadata = {}
        topics_view = _create_view()
        lif_out.views = [topics_view]

        topics_view.annotations.append(markable_annotation(lif_in))
        doc = prepare_text_for_lda(lif_in.text.value)
        bow = dictionary.doc2bow(doc)
        for topic in lda.get_document_topics(bow):
            topic_id += 1
            # these are tuples of topic_id and score
            lemmas = get_lemmas_from_topic_name(topic_idx.get(topic[0]))
            # print('   %3d  %.04f  %s' % (topic[0], topic[1], lemmas))
            topics_view.annotations.append(
                topic_annotation(topic, topic_id, lemmas))
        lif_out.write(fname=fname_out, pretty=True)


def prepare_text_for_lda(text):
    def tokenize(sentence):
        tokens = word_tokenize(sentence)
        return [get_lemma(tok.lower()) for tok in tokens
                if len(tok) > 4 and tok not in STOPWORDS]
    sentences = sent_tokenize(text)
    return [tokenize(sent) for sent in sentences]


def prepare_text_for_lda(text):
    tokens = word_tokenize(text)
    return [get_lemma(tok.lower()) for tok in tokens
            if len(tok) > 4 and tok not in STOPWORDS]


def markable_annotation(lif_obj):
    return Annotation({"id": "m1",
                       "@type": 'http://vocab.lappsgrid.org/Markable',
                       "start": 0,
                       "end": len(lif_obj.text.value)})


def topic_annotation(topic, topic_id, lemmas):
    return Annotation({"id": "t{:d}".format(topic_id),
                       "@type": 'http://vocab.lappsgrid.org/SemanticTag',
                       "target": "m1",
                       "features": {
                           "type": "gensim-topic",
                           "topic_id": topic[0],
                           "topic_score": "{:.04f}".format(topic[1]),
                           "topic_name": lemmas}})


def get_lemma(word):
    lemma = wn.morphy(word)
    return word if lemma is None else lemma


def get_lemmas_from_topic_name(name):
    if name is None:
        return None
    else:
        lemmas = [x.split('*"')[1][:-1] for x in name.split(' + ')]
        return ' '.join(lemmas)


def _create_view():
    view_spec = {
        'id': "topics",
        'metadata': {
            'contains': {
                'http://vocab.lappsgrid.org/Markable': {
                    'producer': 'generate_topics.py'},
                'http://vocab.lappsgrid.org/SemanticTag': {
                    'producer': 'generate_topics.py'}}},
        'annotations': []}
    return View(json_obj=view_spec)


if __name__ == '__main__':

    lif_dir, top_dir = sys.argv[1:3]
    # build_model(lif_dir)
    # print_model()
    generate_topics(lif_dir, top_dir)
