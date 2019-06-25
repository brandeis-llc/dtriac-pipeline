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
        query = { "query": { "match_all": {} } }
        return Result(result=self.es.search(index=self.index, body=query, size=500,
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
        self.total_hits = self._get_total_hits()
        self.sources = [hit.source for hit in self.hits]
        self.scroll_id = result.get('_scroll_id')

    def __str__(self):
        return "&lt;Result %s>" % self.total_hits

    def _get_total_hits(self):
        try:
            # Elastic 7.1.1
            return self.result['hits']['total']['value']
        except TypeError:
            # Elastic 6.4.2
            return self.result['hits']['total']

    def is_tech_query(self):
        bool = self.query_json['query']['bool']
        if len(bool.keys()) == 1:
            matches = list(bool.values())[0]
            if len(matches) == 1:
                pair = matches[0].get('match', matches[0].get('match_phrase'))
                if 'technology' in pair:
                    return pair['technology']
        return False

    def sorted_sources(self):
        from operator import attrgetter
        self.sources.sort(key = attrgetter('docid'))
        return self.sources

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

    def sentence_groups(self, sentence_index):
        groups = SentenceGroups(self.source.docid, self.result.query_json)
        for match, query in groups.queries:
            result = sentence_index.search(query)
            groups.add_group(SentenceGroup(match, query, result))
        return groups


class SentenceGroups(object):

    """A SentenceGroups instance is defined by a document and the query that ran
    over that document. """

    def __init__(self, docid, query):
        self.docid = docid
        self.query = query
        self.queries = []
        self.groups = []
        self.convert_query()
        
    def convert_query(self):
        """Takes the query used for the document index and transforms it into a list of
        queries for the sentences index. There will be a query for each element of
        the original query, but it will be put into an AND with a query for the
        docid."""
        # TODO: one thing that goes a bit wrong is when you search on pred AND arg,
        # in which case the AND link gets lost and will be replaced with an OR.
        bool = self.query['query']['bool']
        matches = bool.get('must', bool.get('should'))
        matches = [m.get('match', m.get('match_phrase')) for m in matches]
        for match in matches:
            match_type = 'match_phrase' if ' ' in list(match.items())[0][1] else 'match'
            query = {
                'query': {
                    'bool': {
                        'must': [
                            { 'match': { 'docid': self.docid } },
                            { match_type: match} ] } } }
            self.queries.append((match, query))

    def add_group(self, group):
        self.groups.append(group)


class SentenceGroup(object):

    """A SentenceGroup is defined by a query """

    def __init__(self, match, query, result):
        self.match = match
        self.query = query
        self.result = result
        self.sentences = []
        for hit in result.hits[:5]:
            self.sentences.append(Sentence(self.match, hit))


class Sentence(object):
    
    def __init__(self, match, hit):
        self.match = match
        self.id = hit.id
        self.score = hit.score
        self.text = hit.source.text
        self.highlight()

    def highlight(self):
        term = list(self.match.items())[0][1]
        searchterm = r'\b%s\b' % term
        matches = list(set(re.findall(searchterm, self.text, flags=re.I)))
        for match in matches:
            self.text = re.sub(r'\b%s\b' % match, "<span class='term'>%s</span>" % match, self.text)



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
