"""load_index.py

Loading documents into the elastic search demo index.

Usage:

$ python load_index.py INDEX_NAME DIRECTORY

Load JSON documents from DIRECTORY into an index named INDEX_NAME.

"""

import os
import sys
import codecs
import json

from elastic import Index


# some default values for experimentation
INDEX_NAME = 'demo'
SOURCES = '/Users/marc/Desktop/projects/dtra/dtra-534/spv1-results-ela'


def read_documents(document_directory):
    documents = []
    for fname in sorted(os.listdir(document_directory)):
        print fname
        fname = os.path.join(document_directory, fname)
        json_obj = json.loads(codecs.open(fname, encoding='utf8').read())
        documents.append(json_obj)
    return documents


if __name__ == '__main__':

    index_name = INDEX_NAME
    source_directory = SOURCES
    if len(sys.argv) > 2:
        index_name = sys.argv[1]
        source_directory = sys.argv[2]
    docs = read_documents(source_directory)
    idx = Index('demo')
    idx.load(docs)
