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
import pickle
import datetime
from pprint import pformat
from collections import Counter

from lif import LIF, Container


def read_sample(fname, lif_directory):
    """Return a set of all filenames in fname, with the extensions stripped. If
    fname is None return the set of file names in lif_directory."""
    # TODO: this is a bit of a holdover from when the sample was just a list and
    # I pulled elements from the list from the full directory, can probably be
    # removed
    print(fname)
    print(lif_directory)
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
        print("WARNING: unexpected number of files found")
    return files


def print_files(fnames, lif_files, ner_files, tex_files, ttk_files, sen_files,
                rel_files, vnc_files, top_files):
    for fname in sorted(fnames):
        print("\n%s" % fname)
        print('   lif: %s' % lif_files.get(fname))
        print('   ner: %s' % ner_files.get(fname))
        print('   tex: %s' % tex_files.get(fname))
        print('   ttk: %s' % ttk_files.get(fname))
        print('   sen: %s' % sen_files.get(fname))
        print('   rel: %s' % rel_files.get(fname))
        print('   vnc: %s' % vnc_files.get(fname))
        print('   top: %s' % top_files.get(fname))


def create_documents(fnames, lif_files, ner_files, tex_files, ttk_files,
                     sen_files, rel_files, vnc_files, top_files, ela):
    """Read all the lif files generate for a document and create JSON files for
    documents, sections and sentences."""
    for fname in sorted(fnames):
        Section.ID = 0
        Sentence.ID = 0
        doc = Document(fname,
                       lif_files[fname], ner_files[fname], tex_files[fname],
                       ttk_files[fname], sen_files[fname], rel_files[fname],
                       vnc_files[fname], top_files[fname])
        doc.pp(prefix='\n')
        doc.write(os.path.join(ela, 'documents'))
        #create_sections(doc)
        #create_sentences(doc)
        if doc.fname.startswith('88'):
            break


def create_sections(doc):
    sections = doc.get_sections()
    for section in sections:
        #print section
        section.write(os.path.join(ela, 'sections'))


def create_sentences(doc):
    sentences = doc.get_sentences()
    for sentence in sentences:
        #sentence.pp()
        sentence.write(os.path.join(ela, 'sentences'))


class Document(object):

    ID = 0

    @classmethod
    def new_id(cls):
        cls.ID += 1
        return cls.ID

    def __init__(self,
                 fname, lif_file, ner_file, tex_file,
                 ttk_file, sen_file, rel_file, vnc_file, top_file):
        """Build a single LIF object with all relevant annotations. The annotations
        themselves are stored in the Annotations object in self.annotations."""
        self.id = Document.new_id()
        self.fname = fname
        self.lif = Container(lif_file).payload
        self._add_views(ner_file, tex_file, ttk_file, sen_file, rel_file,
                        vnc_file, top_file)
        self.lif.metadata["filename"] = self.fname
        self.lif.metadata["title"] = self._get_title()
        self.lif.metadata["year"] = self._get_year()
        self.lif.metadata["abstract"] = self._get_abstract()
        self.annotations = Annotations(fname, doc=self, docid=self.id,
                                       text=self.lif.text.value)
        self.annotations.text = self.lif.text.value
        self._collect_allowed_offsets()
        self._collect_annotations()

    def _add_views(self, ner_file, tex_file, ttk_file, sen_file, rel_file,
                   vnc_file, top_file):
        # Note that some files contain LIF objects and others contain Containers
        # with LIF embedded. The view we are looking for is the first or second,
        # depending on how the processor for those data was set up.
        self._add_view("ner", Container(ner_file).payload.views[1])
        self._add_view("tex", Container(tex_file).payload.views[1])
        self._add_view("ttk", LIF(ttk_file).views[1])
        self._add_view("sen", LIF(sen_file).views[0])
        self._add_view("rel", Container(rel_file).payload.views[1])
        try:
            self._add_view("vnc", LIF(vnc_file).views[0])
        except ValueError:
            # for the cases where the VNC component fails
            print("WARNING: no json object")
            print("         %s" % os.path.basename(vnc_file))
        self._add_view("top", LIF(top_file).views[0])

    def _add_view(self, identifier, view):
        view.id = identifier
        self.lif.views.append(view)

    def _get_title(self):
        view = self.get_view("structure")
        text = self.lif.text.value
        for annotation in view.annotations:
            if annotation.type.endswith('Title'):
                return text[annotation.start:annotation.end]

    def _get_year(self):
        year = self.lif.metadata.get('year')
        if year is not None:
            return year
        else:
            # not all files have the year in the metadata, fake it with some
            # analyses of the references
            year = 0
            current_year = datetime.datetime.now().year
            for ref in self.lif.metadata.get('references', []):
                year = max(year, min(current_year, ref.get('year', 0)))
            return year if year > 0 else None

    def _get_abstract(self):
        view = self.get_view("structure")
        text = self.lif.text.value
        for annotation in view.annotations:
            if annotation.type.endswith('Abstract'):
                return text[annotation.start:annotation.end]

    def get_view(self, identifier):
        return self.lif.get_view(identifier)

    def get_text(self, annotation):
        return self.lif.text.value[annotation.start:annotation.end]

    def _collect_allowed_offsets(self):
        """This creates a set of all character offsets that are in indexable areas of
        the document, that is, they are in sentences of type=normal."""
        view = self.get_view("sen")
        self.allowed_offsets = set()
        for s in view.annotations:
            if s.features.get('type') == 'normal':
                for p in range(s.start, s.end):
                    self.allowed_offsets.add(p)

    def _collect_annotations(self):
        self._collect_authors()
        self._collect_topics()
        self._collect_sentences()
        self._collect_technologies()
        self._collect_entities()
        self._collect_events()
        self._collect_verbnet_classes()
        self._collect_relations()

    def _collect_authors(self):
        """Just collect authors as a list and put them in the index."""
        authors = [author['name'] for author in self.lif.metadata['authors']]
        self.annotations.authors = authors

    def _collect_topics(self):
        """Collect the topics and put them on a list in the index."""
        view = self.get_view("top")
        for annotation in view.annotations:
             if annotation.type.endswith('SemanticTag'):
                 topic_name = annotation.features['topic_name']
                 self.annotations.topics.append(topic_name)
                 for topic_element in topic_name.split():
                     self.annotations.topic_elements.append(topic_element)

    def _collect_sentences(self):
        view = self.get_view("sen")
        for s in view.annotations:
            if s.features.get('type') == 'normal':
                self.annotations.sentences.append(s)

    def _collect_entities(self):
        view = self.get_view("ner")
        for entity in view.annotations:
            entity.text = self.get_text(entity)
            category = entity.features.get('category')
            if category == 'person':
                self.annotations.persons.add(entity)
            elif category == 'location':
                self.annotations.locations.add(entity)
            elif category == 'organization':
                self.annotations.organizations.add(entity)
        self.annotations.persons.finish()
        self.annotations.locations.finish()
        self.annotations.organizations.finish()

    def _collect_technologies(self):
        view = self.get_view("tex")
        for tech in view.annotations:
            tech.text = self.get_text(tech)
            self.annotations.technologies.add(tech)
        self.annotations.technologies.finish()

    def _collect_events(self):
        view = self.get_view("ttk")
        for annotation in view.annotations:
            if annotation.type.endswith("Event"):
                annotation.text = self.get_text(annotation)
                self.annotations.events.add(annotation)
            elif annotation.type.endswith("TimeExpression"):
                annotation.text = self.get_text(annotation)
                self.annotations.times.add(annotation)
        self.annotations.events.finish()
        self.annotations.times.finish()

    def _collect_verbnet_classes(self):
        view = self.get_view("vnc")
        if view is None:
            return
        for annotation in view.annotations:
            if annotation.features.get('tags') == [u'None']:
                continue
            annotation.text =  self.get_text(annotation)
            self.annotations.vnc.add(annotation)
        self.annotations.vnc.finish()

    def _collect_relations(self):
        view = self.get_view("rel")
        idx = { anno.id: anno for anno in view.annotations if anno.type.endswith('Markable') }
        for annotation in view.annotations:
            if annotation.type.endswith('GenericRelation'):
                relation = Relation(self, idx, annotation)
                self._add_verbnet_class(relation)
                if relation.is_acceptable():
                    self.annotations.relations.append(relation)

    def _add_verbnet_class(self, relation):
        pass

    def get_sections(self):
        view = self.get_view("structure")
        sections = [a for a in view.annotations if a.type.endswith('Section')]
        return [Section(self, section) for section in sections]

    def get_sentences(self):
        # take the sentences view, it has the sentences copied from the ttk
        # view, but with the type (normal vs crap) added
        view = self.get_view("sen")
        sentences = [a for a in view.annotations if a.type.endswith('Sentence')]
        return [Sentence(self, s) for s in sentences
                if s.features.get('type') == 'normal']

    def write(self, dirname):
        self.annotations.write(os.path.join(dirname, "%04d.json" % self.id),
                               self.lif.metadata["title"],
                               self.lif.metadata["year"],
                               self.lif.metadata["abstract"])
        self.annotations.write_index(os.path.join(dirname, "%04d.pckl" % self.id))

    def pp(self, prefix=''):
        views = ["%s:%d" % (view.id, len(view)) for view in self.lif.views]
        print("%s<Document id=%s '%s'>" % (prefix, self.id, self.fname))
        print("    <Views %s>" % ' '.join(views))
        print("    %s\n" % self.annotations)


class Relation(object):

    def __init__(self, document, idx, annotation):
        self.document = document
        self.annotation = annotation
        self.pred = idx[annotation.features['relation']]
        self.arg1 = idx[annotation.features['arguments'][0]]
        self.arg2 = idx[annotation.features['arguments'][1]]
        self.pred_text = document.get_text(self.pred)
        self.arg1_text = document.get_text(self.arg1)
        self.arg2_text = document.get_text(self.arg2)
        self.start = self.pred.start
        self.end = self.pred.end
        for arg in self.arg1, self.arg2:
            self.start = min(self.start, arg.start)
            self.end = max(self.start, arg.end)
        self.vnc = None

    def __str__(self):
        return "<Relation %d-%d %s>" \
            % (self.start, self.end, self.pred_text.replace("\n", ' '))

    def is_acceptable(self):
        return self.predicate_is_event() and self.arguments_contain_entity()

    def predicate_is_event(self):
        offsets = list(range(self.pred.start, self.pred.end))
        for offset in offsets:
            if offset in self.document.annotations.events.get_index():
                last = self.document.annotations.events.get_index()[offset][0] - 1
                if last in offsets:
                    return True
        return False

    def arguments_contain_entity(self):
        offsets_a1 = list(range(self.arg1.start, self.arg1.end))
        offsets_a2 = list(range(self.arg2.start, self.arg2.end))
        annotations = self.document.annotations
        return (self._in_annotation_idx(offsets_a1, annotations.technologies)
                or self._in_annotation_idx(offsets_a1, annotations.persons)
                or self._in_annotation_idx(offsets_a1, annotations.organizations)
                or self._in_annotation_idx(offsets_a1, annotations.locations)
                or self._in_annotation_idx(offsets_a2, annotations.technologies)
                or self._in_annotation_idx(offsets_a2, annotations.persons)
                or self._in_annotation_idx(offsets_a2, annotations.organizations)
                or self._in_annotation_idx(offsets_a2, annotations.locations))

    def _in_annotation_idx(self, offsets, indexed_annotations):
        """Checks whether the one of the offsets is included in the annotation index as
        a starting offset while the corresponding closing offset is also in the list of
        offsets."""
        for offset in offsets:
            if offset in indexed_annotations.idx_p1_p2_id:
                last = indexed_annotations.idx_p1_p2_id[offset][0] - 1
                if last in offsets:
                    return True
        return False


class DocumentElement(object):

    def create_index(self):
        idx = self.document.annotations
        self.annotations = Annotations(self.document.fname, self.docid, self.id)
        self.annotations.text = idx.text[self.start:self.end]
        self.annotations.authors = idx.authors
        self.annotations.technologies.add_all(self.filter(idx.technologies.annotations))
        self.annotations.persons.add_all(self.filter(idx.persons.annotations))
        self.annotations.locations.add_all(self.filter(idx.locations.annotations))
        self.annotations.organizations.add_all(self.filter(idx.organizations.annotations))
        self.annotations.events.add_all(self.filter(idx.events.annotations))
        self.annotations.times.add_all(self.filter(idx.times.annotations))
        self.annotations.relations = self.filter(idx.relations)

    def filter(self, annotations):
        answer = []
        for annotation in annotations:
            if self.contains(annotation):
                answer.append(annotation)
        return answer

    def contains(self, annotation):
        """Return True if the element includes the annotation. Note that the annotation
        is an instance of lif.Annotation or an instance of Relation."""
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
            (self.docid, self.id, self.start, self.end, self.annotations.count_string())

    def write(self, output_dir):
        output_file = os.path.join(output_dir, "%04d-%04d.json" % (self.docid, self.id))
        self.annotations.write(output_file)


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
            (self.docid, self.id, self.start, self.end, self.annotations.count_string())

    def write(self, output_dir):
        output_file = os.path.join(output_dir, "%04d-%04d.json" % (self.docid, self.id))
        self.annotations.write(output_file)

    def pp(self):
        print(self)


class Annotations(object):

    """Object that holds all annotations for a file as well as the text of the
    document. Annotations include (1) metadata like authors and topics, which
    are not associated with offsets, (2) entities and events, which all are
    associated with text positions, and (3) relations, which currently have a
    special status in that they are the only complex annotation."""

    def __init__(self, fname, doc=None, docid=None, sentid=None, text=None):
        self.fname = fname
        self.doc = doc
        self.docid = "%04d" % docid
        if sentid is not None:
            self.docid = "%04d-%04d" % (docid, sentid)
        self.text = text
        self.authors = []
        self.year = None
        self.topics = []
        self.topic_elements = []
        self.sentences = []
        self.text = None
        self.technologies = IndexedAnnotations(doc, "technologies")
        self.persons = IndexedAnnotations(doc, "persons")
        self.organizations = IndexedAnnotations(doc, "organizations")
        self.locations = IndexedAnnotations(doc, "locations")
        self.events = IndexedAnnotations(doc, "events")
        self.times = IndexedAnnotations(doc, "times")
        self.vnc = IndexedAnnotations(doc, "vnc")
        self.relations = []

    def __str__(self):
        return "<Index %s %s>" % (self.docid, self.count_string())

    def count_string(self):
        return "tech:%d person:%d loc:%d org:%d event:%d time:%d rel:%d top:%d" \
            % (len(self.technologies), len(self.persons), len(self.locations),
               len(self.organizations), len(self.events), len(self.times),
               len(self.relations), len(self.topics))

    def write(self, fname, title=None, year=None, abstract=None):
        """Writes the document with the search fields to a json file."""
        json_object = {
            "text": self.text,
            "docid": self.docid,
            "docname": self.fname,
            "title": title,
            "year": year,
            "author": self.authors,
            "topic": self.topics,
            "topic_element": self.topic_elements,
            "abstract": abstract,
            "technology": self.technologies.get_text_strings(),
            "person": self.persons.get_text_strings(),
            "location": self.locations.get_text_strings(),
            "organization": self.organizations.get_text_strings(),
            "event": self.events.get_text_strings(),
            "time": self.times.get_text_strings(),
            "relation": [self.relation_dict(r) for r in self.relations] }
        with codecs.open(fname, 'w', encoding='utf8') as fh:
            fh.write(json.dumps(json_object, sort_keys=True, indent=4))

    def write_index(self, fname):
        """Writes the text, the offset index and the lemma index to a pickle
        file. The offsets attribute has, for each category, mappings from the
        category string to a string that encodes all offsets where the entity
        occurs. The lemma property maps lemmas to full phrases as they occur in
        the offsets index."""
        # TODO: this does not yet include relations
        # TODO: should include sentence boundaries
        json_object = {
            "text": self.text,
            "offsets": {
                "technology": self.technologies.idx_text_offsets,
                "person": self.persons.idx_text_offsets,
                "location": self.locations.idx_text_offsets,
                "organization": self.organizations.idx_text_offsets,
                "event": self.events.idx_text_offsets,
                "time": self.times.idx_text_offsets
            },
            "lemmas": {
                "technology": self.technologies.idx_lemma_phrase,
                "person": self.persons.idx_lemma_phrase,
                "location": self.locations.idx_lemma_phrase,
                "organization": self.organizations.idx_lemma_phrase,
                "event": self.events.idx_lemma_phrase,
                "time": self.times.idx_lemma_phrase
            }
        }
        with open(fname, 'wb') as fh:
            pickle.dump(json_object, fh)

    def relation_dict(self, relation):
        return { "pred": relation.pred_text,
                 "vnc": relation.vnc,
                 "arg1": relation.arg1_text,
                 "arg2": relation.arg2_text }

    def pp(self, indent=''):
        print("%s%s\n" % (indent, self))


class IndexedAnnotations(object):

    """An index of all annotation in a file for a particualr type (like "person" or
    "technology). Keeps the lize, the list of annotations, a set of text strings
    and a couple of dictionaries."""

    def __init__(self, doc, annotation_type):
        self.doc = doc
        self.type = annotation_type
        self.size = 0
        self.texts = set()
        self.annotations = []
        self.idx_p1_p2_id = {}
        self.idx_text_offsets = {}
        self.idx_lemma_phrase = {}

    def __len__(self):
        return self.size

    def __str__(self):
        return "<IndexedAnnotations %s count=%d>" % (self.type, self.size)

    def add(self, annotation):
        self.texts.add(annotation.text)
        self.annotations.append(annotation)

    def add_all(self, annotations):
        for annotation in annotations:
            self.add(annotation)
        self.finish()

    def finish(self):
        """Set the size variable and populate the three indexes."""
        self.size = len(self.texts)
        self._filter_annotations()
        self.idx_p1_p2_id = { a.start: (a.end, a.id) for a in self.annotations }
        for anno in self.annotations:
            self.idx_text_offsets.setdefault(anno.text, []).append("%d-%d" % (anno.start, anno.end))
        for text, offsets in self.idx_text_offsets.items():
            self.idx_text_offsets[text] = ' '.join(offsets)
        for phrase in self.idx_text_offsets:
            for lemma in phrase.split():
                if lemma != phrase:
                    self.idx_lemma_phrase.setdefault(lemma, []).append(phrase)
        # self.print_annotations_index()

    def get_text_strings(self):
        return sorted(self.texts)

    def get_index(self):
        return self.idx_p1_p2_id

    def print_annotations_index(self):
        print(self.type)
        for text in sorted(self.idx_text_offsets):
            print("  %s  %s" % (text, self.idx_text_offsets[text]))

    def _filter_annotations(self):
        """Filter the list of annotations to make sure that annotations are allowed only
        if they fall within sentences with type=normal, also update the texts."""
        offsets = self.doc.allowed_offsets
        self.annotations = [anno for anno in self.annotations
                            if self._offsets_are_allowed(anno)]
        self.texts = set([a.text for a in self.annotations])

    def _offsets_are_allowed(self, annotation):
        for p in range(annotation.start, annotation.end):
            if p not in self.doc.allowed_offsets:
                return False
        return True


if __name__ == '__main__':

    lif, ner, tex, ttk, sen, rel, vnc, top, ela = sys.argv[1:10]
    sample = None if len(sys.argv) < 11 else sys.argv[10]

    fnames = read_sample(sample, lif)
    lif_files = get_files(fnames, lif, '.lif')
    ner_files = get_files(fnames, ner, '.lif')
    tex_files = get_files(fnames, tex, '.lif')
    ttk_files = get_files(fnames, ttk, '.lif')
    sen_files = get_files(fnames, sen, '.lif')
    rel_files = get_files(fnames, rel, '.lif')
    vnc_files = get_files(fnames, vnc, '.lif')
    top_files = get_files(fnames, top, '.lif')
    #print_files(fnames, lif_files, ner_files, tex_files, ttk_files,
    #            sen_files, rel_files, vnc_files, top_files)
    create_documents(fnames, lif_files, ner_files, tex_files, ttk_files,
                     sen_files, rel_files, vnc_files, top_files, ela)
