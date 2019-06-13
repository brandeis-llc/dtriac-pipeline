"""create_index_docs.py 

Merge information from different views and export JSON files that can be loaded
into ElasticSearch.

Usage:

$ python create_index_docs.py LIF NER TEX TTK REL TOP ELA SAMPLE_FILE?

The first six arguments are all the input directories with the following
content:

LIF - The LIF files created from the output of Science Parse
NER - Result of adding named entities to LIF
TEX - Result of adding technologies to LIF
TTK - Result of adding Tarsqi analysis to LIF
REL - Result of adding ReVerb analysis to LIF
TOP - Result of adding ReVerb analysis to LIF

The ELA argument refers to the output directory.

The optional SAMPLE_FILE contains a list of all files that should be included by
this script. Without it, all files in LIF will be used and it will be assumed
that NER, TEX, TTK and REL have analyses for all the files in LIF.

See create_index_docs.sh for an example invocation.

"""

import os
import sys
import codecs
import json
from collections import Counter

from lif import LIF, Container


def read_sample(fname, lif_directory):
    """Return a set of all filenames in fname, with the extensions stripped. If
    fname is None return the set of file names in lif_directory."""
    if fname is not None:
        extension = '.pdf.json.txt'
        fnames = [fname.strip() for fname in codecs.open(fname).readlines()]
    else:
        extension = '.lif'
        fnames = os.listdir(lif_directory)
    return set([fname[:-len(extension)] for fname in fnames])


def get_files(fnames, directory, extension):
    files = {}
    for fname in sorted(os.listdir(directory)):
        stripped_fname = fname[:-len(extension)]
        if stripped_fname in fnames:
            files[stripped_fname] = os.path.join(directory, fname)
    if len(fnames) != len(files):
        print "WARNING: unexpected number of files found"
    return files


def print_files(fnames, lif_files, ner_files, tex_files, ttk_files, rel_files, top_files):
    for fname in sorted(fnames):
        print("\n%s" % fname)
        print('   lif: %s' % lif_files.get(fname))
        print('   ner: %s' % ner_files.get(fname))
        print('   tex: %s' % tex_files.get(fname))
        print('   ttk: %s' % ttk_files.get(fname))
        print('   rel: %s' % rel_files.get(fname))
        print('   top: %s' % top_files.get(fname))


def create_documents(fnames, lif_files, ner_files, tex_files, ttk_files,
                     rel_files, top_files, ela):
    for fname in sorted(fnames):
        Section.ID = 0
        Sentence.ID = 0
        doc = Document(fname,
                       lif_files[fname], ner_files[fname], tex_files[fname],
                       ttk_files[fname], rel_files[fname], top_files[fname])
        doc.collect_annotations()
        print
        doc.pp()
        outfile = os.path.join(ela, 'documents', doc.fname + '.json')
        json = doc.write(outfile)
        create_sections(doc)
        create_sentences(doc)
        if doc.fname.startswith('8'):
            break


def create_sections(doc):
    sections = doc.get_sections()
    for section in sections:
        print section
        section.write(os.path.join(ela, 'sections'))


def create_sentences(doc):
    sentences = doc.get_sentences()
    for sentence in sentences:
        sentence.write(os.path.join(ela, 'sentences'))



class Document(object):

    ID = 0

    def __init__(self,
                 fname, lif_file, ner_file, tex_file,
                 ttk_file, rel_file, top_file):
        Document.ID += 1
        self.id = Document.ID
        self.fname = fname
        # Note that some files contain LIF objects and others contain Containers
        # with LIF embedded
        self.lif = Container(lif_file).payload
        self.ner = Container(ner_file).payload
        self.tex = Container(tex_file).payload
        self.ttk = LIF(ttk_file)
        self.rel = Container(rel_file).payload
        self.top = LIF(top_file)
        # the view we look for is always the second one
        self._add_view("ner", self.ner.views[1])
        self._add_view("tex", self.tex.views[1])
        self._add_view("ttk", self.ttk.views[1])
        self._add_view("rel", self.rel.views[1])
        self._add_view("top", self.top.views[0])
        self.index = IndexData(fname, self.id)
        self.index.text = self.lif.text.value
        self.lif.metadata["filename"] = self.fname

    def _add_view(self, identifier, view):
        view.id = identifier
        self.lif.views.append(view)

    def get_view(self, identifier):
        return self.lif.get_view(identifier)

    def get_text(self, annotation):
        return self.lif.text.value[annotation.start:annotation.end]

    def get_text_ner(self, annotation):
        # exists for now since the primary data are out of sync
        return self.ner.text.value[annotation.start:annotation.end]

    def get_text_rel(self, annotation):
        # exists for now since the primary data are out of sync
        return self.rel.text.value[annotation.start:annotation.end]

    def collect_annotations(self):
        self._collect_authors()
        self._collect_topics()
        self._collect_technologies()
        self._collect_entities()
        self._collect_events()
        self.index.index()
        self._collect_relations()

    def _collect_authors(self):
        authors = [author['name'] for author in self.lif.metadata['authors']]
        self.index.authors = authors

    def _collect_topics(self):
        view = self.get_view("top")
        topics = []
        for annotation in view.annotations:
             if annotation.type.endswith('SemanticTag'):
                 topics.append(annotation.features['topic_name'])
        self.index.topics = topics

    def _collect_entities(self):
        view = self.get_view("ner")
        persons = set()
        locations = set()
        organizations = set()
        for entity in view.annotations:
            entity.text = self.get_text_ner(entity)
            category = entity.features.get('category')
            #if category in ('person', 'organization', 'location'):
            #    print entity, category, self.get_text(entity)
            if category == 'person':
                persons.add(entity)
            elif category == 'location':
                locations.add(entity)
            elif category == 'organization':
                organizations.add(entity)
        self.index.persons = sorted(list(persons))
        self.index.locations = sorted(list(locations))
        self.index.organizations = sorted(list(organizations))

    def _collect_technologies(self):
        view = self.get_view("tex")
        technologies = set()
        for tech in view.annotations:
            tech.text = self.get_text(tech)
            technologies.add((tech))
        self.index.technologies = sorted(list(technologies))

    def _collect_events(self):
        view = self.get_view("ttk")
        events = set()
        times = set()
        for annotation in view.annotations:
            if annotation.type.endswith("Event"):
                annotation.text = self.get_text(annotation)
                events.add(annotation)
            elif annotation.type.endswith("TimeExpression"):
                annotation.text = self.get_text(annotation)
                times.add(annotation)
        self.index.events = sorted(list(events))
        self.index.times = sorted(list(times))

    def _collect_relations(self):
        view = self.get_view("rel")
        idx = { anno.id: anno for anno in view.annotations if anno.type.endswith('Markable') }
        for annotation in view.annotations:
            if annotation.type.endswith('GenericRelation'):
                relation = Relation(self, idx, annotation)
                if relation.is_acceptable():
                    self.index.relations.append(relation)

    def get_sections(self):
        view = self.get_view("structure")
        sections = [a for a in view.annotations if a.type.endswith('Section')]
        return [Section(self, section) for section in sections]

    def get_sentences(self):
        view = self.get_view("ttk")
        sentences = [a for a in view.annotations if a.type.endswith('Sentence')]
        return [Sentence(self, sentence) for sentence in sentences]

    def write(self, fname):
        self.index.write(fname)

    def pp(self):
        views = ["%s:%d" % (view.id, len(view)) for view in self.lif.views]
        print "<Document '%s'>" % self.fname
        print "    <Views %s>" % ' '.join(views)
        print "    %s\n" % self.index


class Relation(object):

    def __init__(self, document, idx, annotation):
        self.document = document
        self.annotation = annotation
        self.pred = idx[annotation.features['relation']]
        self.arg1 = idx[annotation.features['arguments'][0]]
        self.arg2 = idx[annotation.features['arguments'][1]]
        self.pred_text = document.get_text_rel(self.pred)
        self.arg1_text = document.get_text_rel(self.arg1)
        self.arg2_text = document.get_text_rel(self.arg2)
        self.start = self.pred.start
        self.end = self.pred.end
        for arg in self.arg1, self.arg2:
            self.start = min(self.start, arg.start)
            self.end = max(self.start, arg.end)

    def __str__(self):
        return "<Relation %d-%d %s>" \
            % (self.start, self.end, self.pred_text.replace("\n", ' '))

    def is_acceptable(self):
        return self.predicate_is_event() and self.arguments_contain_entity()

    def predicate_is_event(self):
        offsets = list(range(self.pred.start, self.pred.end))
        for offset in offsets:
            if offset in self.document.index.idx_events:
                last = self.document.index.idx_events[offset][0] - 1
                if last in offsets:
                    return True
        return False

    def arguments_contain_entity(self):
        offsets_a1 = list(range(self.arg1.start, self.arg1.end))
        offsets_a2 = list(range(self.arg2.start, self.arg2.end))
        index = self.document.index
        return (self.offsets_contain_idx_element(offsets_a1, index.idx_technologies)
                or self.offsets_contain_idx_element(offsets_a1, index.idx_persons)
                or self.offsets_contain_idx_element(offsets_a1, index.idx_organizations)
                or self.offsets_contain_idx_element(offsets_a1, index.idx_locations)
                or self.offsets_contain_idx_element(offsets_a2, index.idx_technologies)
                or self.offsets_contain_idx_element(offsets_a2, index.idx_persons)
                or self.offsets_contain_idx_element(offsets_a2, index.idx_organizations)
                or self.offsets_contain_idx_element(offsets_a2, index.idx_locations))

    def offsets_contain_idx_element(self, offsets, idx):
        for offset in offsets:
            if offset in idx:
                last = idx[offset][0] - 1
                if last in offsets:
                    return True
        return False


class DocumentElement(object):

    def create_index(self):
        self.index = IndexData(self.document.fname, self.docid, self.id)
        self.index.text = self.document.index.text[self.start:self.end]
        self.index.authors = self.document.index.authors
        self.index.technologies = self.filter(self.document.index.technologies)
        self.index.persons = self.filter(self.document.index.persons)
        self.index.locations = self.filter(self.document.index.locations)
        self.index.organizations = self.filter(self.document.index.organizations)
        self.index.events = self.filter(self.document.index.events)
        self.index.times = self.filter(self.document.index.times)
        self.index.relations = self.filter(self.document.index.relations)

    def filter(self, annotations):
        answer = []
        for annotation in annotations:
            if self.contains(annotation):
                answer.append(annotation)
        return answer

    def contains(self, annotation):
        """Return True if the element includes the annotation. Note that the annotation
        is in instance of lif.Annotation."""
        return annotation.start >= self.start and annotation.end <= self.end


class Section(DocumentElement):

    ID = 0

    def __init__(self, document, section):
        Section.ID += 1
        self.id = Section.ID
        self.docid = document.id
        self.document = document
        self.start = section.start
        self.end = section.end
        self.tag = section
        self.create_index()

    def __str__(self):
        return "<Section %04d:%04d %d-%d %s>" % \
            (self.docid, self.id, self.start, self.end, self.index.count_string())

    def write(self, output_dir):
        output_file = os.path.join(output_dir, "%04d-%04d.json" % (self.docid, self.id))
        self.index.write(output_file)


class Sentence(DocumentElement):

    ID = 0

    def __init__(self, document, sentence):
        Sentence.ID += 1
        self.id = Sentence.ID
        self.docid = document.id
        self.document = document
        self.start = sentence.start
        self.end = sentence.end
        self.tag = sentence
        self.create_index()

    def __str__(self):
        return "<Sentence %04d:%04d %d-%d %s>" % \
            (self.docid, self.id, self.start, self.end, self.index.count_string())

    def write(self, output_dir):
        output_file = os.path.join(output_dir, "%04d-%04d.json" % (self.docid, self.id))
        self.index.write(output_file)


class IndexData(object):

    def __init__(self, fname, docid, sentid=None):
        self.fname = fname
        self.docid = "%04d" % docid
        if sentid is not None:
            self.docid = "%04d-%04d" % (docid, sentid)
        self.authors = []
        self.topics = []
        self.text = None
        self.technologies = []
        self.persons = []
        self.organizations = []
        self.locations = []
        self.events = []
        self.times = []
        self.relations = []

    def __str__(self):
        return "<Index %s %s>" % (self.docid, self.count_string())

    def index(self):
        self.idx_events = {}
        for event in self.events:
            self.idx_events[event.start] = (event.end, event.id)
        self.idx_technologies = { t.start: (t.end, t.id) for t in self.technologies }
        self.idx_persons = { t.start: (t.end, t.id) for t in self.persons }
        self.idx_locations = { t.start: (t.end, t.id) for t in self.locations }
        self.idx_organizations = { t.start: (t.end, t.id) for t in self.organizations }

    def count_string(self):
        return "auth:%d tech:%d person:%d loc:%d org:%d event:%d time:%d rel:%d top:%d" \
            % (len(self.authors), len(self.technologies), len(self.persons),
               len(self.locations), len(self.organizations), len(self.events),
               len(self.times), len(self.relations), len(self.topics))

    def write(self, fname):
        json_object = {
            "text": self.text,
            "docid": self.docid,
            "docname": self.fname,
            "author": self.authors,
            "topic": self.topics,
            "technology": [t.text for t in self.technologies],
            "person": [p.text for p in self.persons],
            "location": [l.text for l in self.locations],
            "organization": [o.text for o in self.organizations],
            "event": [e.text for e in self.events],
            "time": [t.text for t in self.times],
            "relation": [self.relation_dict(r) for r in self.relations] }
        with codecs.open(fname, 'w', encoding='utf8') as fh:
            fh.write(json.dumps(json_object, sort_keys=True, indent=4))

    def relation_dict(self, relation):
        return { "pred": relation.pred_text,
                 "arg1": relation.arg1_text,
                 "arg2": relation.arg2_text }

    def pp(self, indent=''):
        print "%s%s\n" % (indent, self)


if __name__ == '__main__':

    lif, ner, tex, ttk, rel, top, ela = sys.argv[1:8]
    sample = None if len(sys.argv) < 9 else sys.argv[8]

    fnames = read_sample(sample, lif)
    lif_files = get_files(fnames, lif, '.lif')
    ner_files = get_files(fnames, ner, '.lif')
    tex_files = get_files(fnames, tex, '.lif')
    ttk_files = get_files(fnames, ttk, '.lif')
    rel_files = get_files(fnames, rel, '.lif')
    top_files = get_files(fnames, top, '.lif')
    #print_files(fnames, lif_files, ner_files, tex_files, ttk_files, rel_files, top_files)
    create_documents(fnames, lif_files, ner_files, tex_files, ttk_files, rel_files, top_files, ela)
