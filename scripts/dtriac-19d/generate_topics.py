"""generate_topics.py

Usage:

$ python3 generate_topics.py -d DATA_DIR -f FILELIST
$ python3 generate_topics.py -d DATA_DIR -f FILELIST -s START -e END
$ python3 generate_topics.py -d DATA_DIR -f FILELIST --crash
$ python3 generate_topics.py --build -d DATA_DIR -f FILELIST -s START -e END
$ python3 generate_topics.py (-h | --help)

The topic model is written to topics/.


"""


import os
import sys
import codecs
import pickle
import getopt

import gensim

import nltk
from nltk import word_tokenize
from nltk.corpus import wordnet as wn

from lif import Container, LIF, View, Annotation
from utils import elements, ensure_directory, time_elapsed


TOPICS_DIR = "topics"
CORPUS_FILE = os.path.join(TOPICS_DIR, 'corpus.pkl')
DICTIONARY_FILE = os.path.join(TOPICS_DIR, 'dictionary.gensim')
MODEL_FILE = os.path.join(TOPICS_DIR, 'model5.gensim')

NUM_TOPICS = 100

STOPWORDS = set(nltk.corpus.stopwords.words('english'))


@time_elapsed
def build_model(data_dir, filelist, start, end):
    """Build a model from scratch using the files as specified in the arguments."""
    print("\nCollecting data")
    text_data = _collect_data(data_dir, filelist, start, end)
    print("\nLoading text data into dictionary")
    dictionary = gensim.corpora.Dictionary(text_data)
    print("\nCreating bag-of-words corpus")
    corpus = [dictionary.doc2bow(text) for text in text_data]
    print(dictionary)
    print("\nCreating LDA model")
    ldamodel = gensim.models.ldamodel.LdaModel(corpus, num_topics=NUM_TOPICS,
                                               id2word=dictionary, passes=15)
    print("\nSaving dictionary, corpus and LDA model to disk\n")
    pickle.dump(corpus, open(CORPUS_FILE, 'wb'))
    dictionary.save(DICTIONARY_FILE)
    ldamodel.save(MODEL_FILE)


def _collect_data(data_dir, filelist, start, end):
    all_data = []
    # especially the first two occur  in most abstracts so let's ignore them
    words_to_ignore = {'title', 'abstract', 'result', 'study'}
    for n, fname in elements(filelist, start, end):
        print("    %07d  %s" % (n, fname))
        fpath = os.path.join(data_dir, 'lif', fname[:-4] + '.lif')
        lif = Container(fpath).payload
        text_data = prepare_text_for_lda(lif.text.value)
        text_data = [w for w in text_data if w not in words_to_ignore]
        all_data.append(text_data)
    token_count = sum([len(d) for d in all_data])
    print('\nToken count = %d' % token_count)
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
    return gensim.corpora.Dictionary.load(DICTIONARY_FILE)


@time_elapsed
def generate_topics(data_dir, filelist, start, end, crash=False):
    lda = load_model()
    topic_idx = {topic_id: topic for topic_id, topic
                 in lda.print_topics(num_topics=NUM_TOPICS)}
    dictionary = load_dictionary()
    for n, fname in elements(filelist, start, end):
        print("%07d  %s" % (n, fname))
        if crash:
            generate_topics_for_file(data_dir, fname, lda, topic_idx, dictionary)
        else:
            try:
                generate_topics_for_file(data_dir, fname, lda, topic_idx, dictionary)
            except Exception as e:
                print('ERROR:', Exception, e)
                sys.stderr.write("ERROR on %07d  %s\n" % (n, fname))


def generate_topics_for_file(data_dir, fname, lda, topic_idx, dictionary):
    topic_id = 0
    fname_in = os.path.join(data_dir, 'lif', fname[:-4] + '.lif')
    fname_out = os.path.join(data_dir, 'top', fname[:-4] + '.lif')
    ensure_directory(fname_out)
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



def usage():
    print("\nUsage:\n"
          + "\n    $ python3 generate_topics.py -d DATA_DIR -f FILELIST"
          + "\n    $ python3 generate_topics.py -d DATA_DIR -f FILELIST -s START -e END"
          + "\n    $ python3 generate_topics.py -d DATA_DIR -f FILELIST --crash"
          + "\n    $ python3 generate_topics.py --build -d DATA_DIR -f FILELIST -s START -e END"
          + "\n    $ python3 generate_topics.py (-h | --help)\n")


if __name__ == '__main__':

    data_dir = '/DATA//sample-01000'
    filelist = '../../data/files-random-01000.txt'

    options = dict(getopt.getopt(sys.argv[1:], 'd:f:s:e:bh', ['crash', 'help', 'build'])[0])
    data_dir = options.get('-d', data_dir)
    filelist = options.get('-f', filelist)
    start = int(options.get('-s', 1))
    end = int(options.get('-e', 1))
    crash = True if '--crash' in options else False
    help_wanted = True if '-h' in options or '--help' in options else False
    build = True if '-b' in options or '--build' in options else False

    if help_wanted:
        usage()
    elif build:
        build_model(data_dir, filelist, start, end)
        print_model()
    else:
        generate_topics(data_dir, filelist, start, end, crash=crash)
