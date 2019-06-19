"""query.py

Example queries for the elastic search demo index.

Mostly copied from ../../query_index.py.py (bad design, must be changed).

"""

import codecs
import json

from elastic import Index


def split_spec(spec):
    s = spec.split(':')
    if len(s) == 1:
        return { "text": spec }
    else:
        return { s[0]: s[1] }


def query(spec):
    spec = spec.strip()
    if spec.find(' ') > -1:
        if spec.startswith('AND'):
            parts = [c.strip() for c in spec.split()][1:]
            return query_and(parts)
        elif spec.startswith('OR'):
            parts = [c.strip() for c in spec.split()][1:]
            return query_or(parts)
        else:
            parts = [c.strip() for c in spec.split()]
            return query_and(parts)
    else:
        return { "query": { "match": split_spec(spec) } }


def query_and(specs):
    return query_bool("must", specs)


def query_or(specs):
    return query_bool("should", specs)


def query_bool(query_type, specs):
    matches = [ {"match": split_spec(spec) } for spec in specs ]
    return { "query": { "bool": { query_type: matches } } }
    

queries = [
    ["(event:acquisition)", query("event:acquisition")],
    ["(person:Markov)    ", query("person:Markov")],
    ["(location:Italy)   ", query("location:Italy")],
    ["pred:involves", query("relation.pred:involves")],
    ["(location:Italy AND person:Markov)", query_and(["person:Markov", "location:Italy"])],
    ["(location:Italy OR person:Markov) ", query_or(["person:Markov", "location:Italy"])]
]


def test_queries(idx):
    print "Retrieving document with id=0024"
    idx.get("0024")
    print "Retrieving document with id=0026"
    idx.get("0026")
    for message, query in queries:
        print '\n', message
        result = idx.search(query)
        result.pp()
    print('')


def test_query(idx, q):
    print q
    json_query = query(q)
    print json_query
    result = idx.search(json_query)
    result.pp()
    print('')


if __name__ == '__main__':

    idx = Index('demo_documents')

    #test_queries(idx)

    for q in ["location:Italy",
              "location:Italy person:Markov the",
              "OR location:Italy person:Markov the"]:
        test_query(idx, q)
