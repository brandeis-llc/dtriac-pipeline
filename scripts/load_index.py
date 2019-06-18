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


def read_documents(document_directory):
    documents = []
    for fname in sorted(os.listdir(document_directory)):
        if fname.endswith('.json'):
            print(fname)
            fname = os.path.join(document_directory, fname)
            json_obj = json.loads(codecs.open(fname, encoding='utf8').read())
            documents.append(json_obj)
    return documents


if __name__ == '__main__':

    if len(sys.argv) > 2:
        index_name = sys.argv[1]
        source_directory = sys.argv[2]
    else:
        exit('ERROR: missing arguments\nUsage: python load_index.py INDEX_NAME DIRECTORY\n')

    docs = read_documents(source_directory)
    idx = Index(index_name)
    idx.load(docs)
