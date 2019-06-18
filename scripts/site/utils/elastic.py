"""elastic.py

Module with some convenience code for acessing an ELastic Search index.

Based on the module with the same name at ../../elastic.py, which is clearly not
so good.

"""

from pprint import pprint
from collections import Counter

from elasticsearch import Elasticsearch 
from elasticsearch.exceptions import NotFoundError


class Index(object):

    def __init__(self, index_name):
        self.index = index_name
        self.es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

    def get_documents(self):
        query = {"query": {"match_all": {}}}
        return Result(self.es.search(index=self.index, body=query, size=100,
                                     _source_includes=['docid', 'title', 'docname']))

    def get(self, doc_id):
        try:
            doc = self.es.get(index=self.index, id=doc_id)
            return doc
        except NotFoundError as e:
            print(e)

    def search(self, query, dribble=False):
        return Result(self.es.search(index=self.index, body=query, size=20, scroll="1m"))


class Result(object):

    """Class to wrap an ElasticSearch result."""
    
    def __init__(self, result):
        self.result = result
        self.hits = [Hit(hit) for hit in self.result['hits']['hits']]
        self.total_hits = self.result['hits']['total']['value']
        self.sources = [hit.source for hit in self.hits]
        self.scroll_id = result.get('_scroll_id')

    def write(self):
        fname = "%04d.txt" % nextint()
        with codecs.open(fname, 'w', encoding='utf8') as fh:
            fh.write(json.dumps(self.result, sort_keys=True, indent=4))

    def pp(self):
        print("\n    Number of hits: %d" % self.total_hits)
        for hit in self.hits:
            print("    %s  %.4f  %s" % (hit.docid, hit.score, hit.docname[:80]))

    def print_sources(self, dribble):
        if dribble:
            sources = self.sources
            print('   Got %d hits' % self.total_hits)
            for source in self.sources:
                print('   %s' % source)


class Hit(object):

    def __init__(self, hit):
        self.hit = hit
        self.id = hit['_id']
        self.score = hit['_score']
        self.source = hit['_source']
        self.docid = self.source.get('docid')
        self.docname = self.source.get('docname')
