"""mallet-topics.py

Script to read the output of mallet processing.

Usage:

$ python mallet_topics.py


See http://mallet.cs.umass.edu/topics.php for commands used to create the
putput. In particular:

Create input for Mallet from a directory:

$ mallet import-dir \
     --input ~/Dropbox/projects/dtra/demo/data/networking \
     --output networking.mallet \
     --keep-sequence \
     --remove-stopwords

Run the model:

$ mallet train-topics \
    --input networking.mallet \
    --num-topics 100 \
    --output-state networking-state.gz \
    --output-doc-topics networking-doc-topics \
    --output-topic-keys networking-topic-keys \
    --num-top-words 10

"""

import os

TOPIC_KEYS = 'networking-topic-keys'
DOCUMENT_TOPICS = 'networking-doc-topics'


def read_topics():
    topics = []
    topics_idx = {}
    for line in open(TOPIC_KEYS):
        topic_id, _, topic_name = line.strip().split('\t')
        topics.append((topic_id, topic_name))
        topics_idx[topic_id] = topic_name
    return topics


def print_topics(topics):
    for topic in topics:
        print(topic)


def read_document_topics(topics):
    document_topics = []
    for line in open(DOCUMENT_TOPICS):
        fields = line.strip().split('\t')
        doc_id = fields.pop(0)
        doc_name = fields.pop(0)
        scores = [float(f) for f in fields]
        results = list(reversed(sorted(list(zip(scores, topics)))))
        results = [result for result in results if result[0] > 0.01]
        document_topics.append((doc_id, doc_name, results))
    return document_topics


def print_document_topics(doc_topics):
    for doc_id, doc_name, results in doc_topics:
        print('\n{}'.format(os.path.basename(doc_name).replace("%20", ' ')))
        for score, (topic, name) in results:
            print("    {:.04f}  {:>2}  {}".format(score, topic, name[:120]))


def print_topics_with_document(doc_topics):
    topics = {}
    for doc_id, doc_name, results in doc_topics:
        for score, (topic, name) in results:
            topics.setdefault((topic, name), []).append(doc_name)
    for topic in sorted(topics):
        print("{} {}".format(topic[0], topic[1]))
        for doc in topics[topic]:
            print("    {}".format(os.path.basename(doc).replace("%20", ' ')))


if __name__ == '__main__':
    topics = read_topics()
    doc_topics = read_document_topics(topics)
    print_document_topics(doc_topics)
    # print_topics_with_document(doc_topics)
