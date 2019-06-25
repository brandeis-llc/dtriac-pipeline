
import os, sys, glob, json, codecs, pprint
from collections import Counter
from flask import request


def get_var(request, var_name):
    if request.method == 'GET':
        return request.args.get(var_name)
    elif request.method == 'POST':
        return request.form.get(var_name)


class Statistics(object):

    def __init__(self, filename):
        json_object = json.loads(codecs.open(filename).read())
        self.years = { int(year): count for (year, count) in json_object["years"].items() }
        self.topics = json_object["topics"]

    def pp(self):
        pprint.pprint(self.years)
        pprint.pprint(self.topics)

    def get_year_data(self):
        """Return a time series for all years from the earliest to the latest in the
        data set. Returns a list of <year, document_count> pairs."""
        year1 = min(self.years)
        year2 = max(self.years)
        return [(year, self.years.get(year, 0)) for year in range(year1, year2)]

    def get_years(self):
        return [year[0] for year in self.get_year_data()]

    def get_year_counts(self):
        return [year[1] for year in self.get_year_data()]

    def get_topic_data(self):
        """Return a list of the 10 most common topics with their counts. Returns a list
        of <topic, document_count> pairs."""
        return Counter(self.topics).most_common(40)

    def get_topics(self):
        return "[%s]" % ', '.join(["'%s'" % topic for (topic, count) in self.get_topic_data()])

    def get_topic_counts(self):
        return [count for (topic, count) in self.get_topic_data()]


class Kibana(object):

    KIBANA_LINK_GENERAL = 'data/kibana_link_general.txt'
    KIBANA_LINK_TERM = 'data/kibana_link_term.txt'

    MORBIUS = 'morbius.cs-i.brandeis.edu'

    def __init__(self):
        self._general = open(Kibana.KIBANA_LINK_GENERAL).read().strip()
        self._term = open(Kibana.KIBANA_LINK_TERM).read().strip()
        if len(os.uname().nodename) == 12:
            self._general = self._general.replace(Kibana.MORBIUS, 'localhost')
            self._term = self._term.replace(Kibana.MORBIUS, 'localhost')

    def link(self):
        return self._general

    def term(self, term):
        term = term.replace('_', '%20')
        term = term.replace(' ', '%20')
        return self._term.replace('FIELD', 'technology').replace('TERM', term)


if __name__ == '__main__':

    stats = Statistics('../data/stats.json')
    print(stats.get_years())
    print(stats.get_topics())
