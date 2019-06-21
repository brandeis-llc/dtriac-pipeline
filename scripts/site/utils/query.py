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
        field = "text"
        value = spec.replace('_', ' ')
    else:
        field = s[0]
        value = s[1].replace('_', ' ')
    match_type = "match_phrase" if ' '  in value else "match"
    return { match_type: { field: value } }


def query(spec):
    parts = [p.strip() for p in spec.strip().split()]
    if parts[0] == 'OR':
        return query_or(parts[1:])
    elif parts[0] == 'AND':
        return query_and(parts[1:])
    else:
        return query_and(parts)


def query_and(specs):
    return query_bool("must", specs)


def query_or(specs):
    return query_bool("should", specs)


def query_bool(query_type, specs):
    matches = [ split_spec(spec) for spec in specs ]
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
    print("Retrieving document with id=0024")
    idx.get("0024")
    print("Retrieving document with id=0026")
    idx.get("0026")
    for message, query in queries:
        print('\n' + message)
        result = idx.search(query)
        result.pp()
    print('')


def test_query(idx, q):
    print(q)
    json_query = query(q)
    print(json_query)
    result = idx.search(json_query)
    result.pp()
    print('')


if __name__ == '__main__':

    idx = Index('demo_documents')

    if False:
        test_queries(idx)

    if False:
        for q in ["location:Italy",
                  "location:Italy person:Markov the",
                  "OR location:Italy person:Markov the"]:
            test_query(idx, q)

    if True:
        print(query("organization:National_Science_Foundation"))
        print(query("OR door organization:National_Science_Foundation"))
        print(query("AND location:Italy organization:National_Science_Foundation"))
        print(query("technology:graph_coupling"))
