"""elastic.py

Module with some convenience code for acessing an ELastic Search index.

Based on the module with the same name at ../../elastic.py, which is clearly not
so good.

"""

import re
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
        return Result(result=self.es.search(index=self.index, body=query, size=100,
                                            _source_includes=['docid', 'title', 'docname']))

    def get(self, doc_id):
        try:
            doc = self.es.get(index=self.index, id=doc_id)
            return doc
        except NotFoundError as e:
            print(e)

    def search(self, query, dribble=False):
        return Result(query_json=query,
                      result=self.es.search(index=self.index, body=query, size=20, scroll="1m"))


class Result(object):

    """Class to wrap an ElasticSearch result."""

    def __init__(self, query_string=None, query_json=None, result=None):
        self.query_string = query_string
        self.query_json = query_json
        self.result = result
        self.hits = [Hit(self, hit) for hit in self.result['hits']['hits']]
        self.total_hits = self.result['hits']['total']['value']
        self.sources = [hit.source for hit in self.hits]
        self.scroll_id = result.get('_scroll_id')

    def __str__(self):
        return "&lt;Result %s>" % self.total_hits

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

    def __init__(self, result, hit):
        self.result = result
        self.hit = hit
        self.id = hit['_id']
        self.score = hit['_score']
        self.source = Source(self, hit['_source'])
        self.docid = self.source.source.get('docid')
        self.docname = self.source.source.get('docname')

    def __str__(self):
        return "&lt;Hit %s>" % self.id

    def sentence_query_results(self, sentence_index):
        queries = convert_query(self.source.docid, self.result.query_json)
        sentences = []
        for match, query in queries:
            result = sentence_index.search(query)
            for hit in result.hits[:5]:
                sentences.append((match, hit.source.text))
        sentences = [highlight(s) for s in sentences]
        return "%s" % '<br/></br/>'.join(['<span class="sentence">%s</span>\n' % s for s in sentences])


class Source(object):

    def __init__(self, hit, source):
        self.hit = hit
        self.source = source
        self.docid = source.get('docid')
        self.docname = source.get('docname')
        self.year = source.get('year')
        self.title = source.get('title')
        self.abstract = source.get('abstract')
        self.text = source.get('text')

    def technologies(self):
        return self.source.get('technology', [])

    def persons(self):
        return self.source.get('person', [])

    def locations(self):
        return self.source.get('location', [])

    def organizations(self):
        return self.source.get('organization', [])

    def technology_links(self):
        return ['<a href="/search?search=true&query=%s">%s</a>' % (tech, tech)
                for tech in self.technologies()]


def convert_query(docid, query):
    """Takes the query used for the document index and transforms it into a list of
    queries for the sentences index. There will be a query for each element of
    the original query, but it will be put into an AND with a query for the
    docid."""
    # TODO: one thing that goes a bit wrong is when you search on pred AND arg,
    # in which case the AND link gets lost and will be replaced with an OR.
    bool = query['query']['bool']
    matches = bool.get('must', bool.get('should'))
    matches = [m.get('match', m.get('match_phrase')) for m in matches]
    queries = []
    for match in matches:
        match_type = 'match_phrase' if ' ' in list(match.items())[0][1] else 'match'
        query = {
            'query': {
                'bool': {
                    'must': [
                        { 'match': { 'docid': docid } },
                        { match_type: match} ] } } }
        queries.append((match, query))
    return queries


def highlight(s):
    # TODO: this should probably be in some other module (even though it uses
    # some pretty idiosyncratic code to get to the term)
    term = list(s[0].items())[0][1]
    sentence = s[1]
    searchterm = r'\b%s\b' % term
    matches = list(set(re.findall(searchterm, sentence, flags=re.I)))
    for match in matches:
        sentence = re.sub(r'\b%s\b' % match, "<span class='term'>%s</span>" % match, sentence)
    return sentence
