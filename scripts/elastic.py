"""elastic.py

Module with some convenience code for acessing an ELastic Search index.

"""

from pprint import pprint

from elasticsearch import Elasticsearch 
from elasticsearch.exceptions import NotFoundError


class Index(object):

    def __init__(self, index_name, index_elements=None):
        self.index = index_name
        self.es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
        if index_elements is not None:
            self.load(index_elements)

    def load(self, elements):
        for i, element in enumerate(elements):
            docid = element.get('docid')
            identifier = i if docid is None else docid
            self.es.index(index=self.index, id=identifier, body=element)

    def print_sources(self, result, dribble):
        if dribble:
            sources = self.get_sources(result)
            print('   Got %d hits' % result['hits']['total']['value'])
            for source in sources:
                print '  ', source

    def get_hits(self, result):
        return [hit for hit in result['hits']['hits']]

    def get_sources(self, result):
        return [hit['_source'] for hit in result['hits']['hits']]

    def get(self, message, doc_id, dribble=False):
        print "\n%s" % message
        try:
            doc = self.es.get(index=self.index, id=doc_id)
            if dribble:
                pprint(doc['_source'])
            return doc
        except NotFoundError as e:
            print e

    def search(self, message, query, dribble=False):
        print "\n%s" % message
        result = self.es.search(index=self.index, body=query)
        self.print_sources(result, dribble)
        return result
    

if __name__ == '__main__':

    entities = [
        {"name": {"first":"john", "last":"doe"}, "age": 27, "interests": ['sports','music']},
        {"name": {"first": "jane", "last": "doe"}, "age": 27, "interests": ["rap music yeah"]},
        {"name": {"first": "june", "last": "doe"}, "age": 65, "interests": ["forestry"]}]

    idx = Index('test_entities', entities)

    queries = [

        ["Matching all elements",
         {'query': {'match_all': {}}}],

        ["Find the young ones",
         {'query': {'match': {'age': 27}}}],

        ["Find the Does",
         {'query': {'match': {'name.last': 'doe'}}}],

        ["Find Jane Doe",
         {'query':
          {'bool':
           {'must': [
               {'match': {'name.first': 'jane'}},
               {'match': {'name.last': 'doe'}}]}}}],

        ["Find Sripi Palaver",
         {'query':
          {'bool':
           {'must': [
               {'match': {'name.first': 'sripi'}},
               {'match': {'name.last':'palaver'}}]}}}],

        ["Find rap or music",
         {'query': {'match': {'interests': 'music rap'}}}],

        ["Find \"rap music\"",
         {'query': {'match_phrase': {'interests': 'rap music'}}}]
        ]

    idx.get("Retrieving document with id=1", 1, dribble=True)
    for message, query in queries:
        idx.search(message, query, dribble=True)
