"""

Example queries for the elastic search demo index.

"""

import codecs
import json

from elastic import Index


def split_spec(spec):
    s = spec.split(':')
    return { s[0]: s[1] }

def query(spec):
    field, value = spec.split(':')
    return { "query": { "match": { field: value } } }

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

    ["(location:Italy AND person:Markov)", query_and(["person:Markov", "location:Italy"])],
    ["(location:Italy OR person:Markov) ", query_or(["person:Markov", "location:Italy"])],
]


if __name__ == '__main__':

    idx = Index('demo')

    idx.get("Retrieving document with id=0024", "0024")
    idx.get("Retrieving document with id=0026", "0026")

    for message, query in queries:
        result = idx.search(message, query)
        result.pp()
    print()
