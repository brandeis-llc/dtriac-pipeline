"""create_index_docs.py

Merge information from different views and export JSON files that can be loaded
into ElasticSearch.

Usage:

$ python create_index_docs.py -d DATA_DIR -f FILELIST (-b BEGIN) (-e END)

Directories:
lif   LIF files created from the OCR output
top   topics
spl   sentence splitting
pos   parts of speech
ner   named entities
tex   technologies
mta   metadata (year and author)
wik   wiki grounding
ela   output


TODO: split multiple names if there is an intervening new line

"""

import os, sys, json
from pprint import pformat
from collections import Counter

from lif import LIF, Container, Annotation
from utils import time_elapsed, elements, ensure_directory, print_element, get_options
import resources

TARSKI_URL = 'http://tarski.cs-i.brandeis.edu'

NAMES = resources.Names()
LOCATIONS = resources.Locations()


# this file gets you to the number of pages
PDFINFO_FILE_PATTERN = '/data/dtriac/dtriac-19d/all/%s/pdfinfo.txt'


@time_elapsed
def create_documents(data_dir, filelist, start, end, crash=False):
    print("$ python3 %s\n" % ' '.join(sys.argv))
    ela_dir = os.path.join(data_dir, 'ela')
    if not os.path.exists(ela_dir):
        os.mkdir(ela_dir)
    for n, fname in elements(filelist, start, end):
        print_element(n, fname)
        if crash:
            create_document(data_dir, fname)
        else:
            try:
                create_document(data_dir, fname)
            except Exception as e:
                print('ERROR:', Exception, e)


def create_document(data_dir, fname):
    # the subdir is really the document identifier
    subdir = os.path.split(fname)[0]
    lif_file = os.path.join(data_dir, 'lif', fname[:-3] + 'lif')
    mta_file = os.path.join(data_dir, 'mta', subdir, '%s.mta.lif' % subdir)
    top_file = os.path.join(data_dir, 'top', fname[:-3] + 'lif')
    ner_file = os.path.join(data_dir, 'ner', subdir, '%s.ner.lif' % subdir)
    sen_file = os.path.join(data_dir, 'sen', subdir, '%s.sen.lif' % subdir)
    tex_file = os.path.join(data_dir, 'tex', subdir, '%s.lup.lif' % subdir)
    wik_file = os.path.join(data_dir, 'wik', subdir, '%s.wik.lif' % subdir)
    if not os.path.exists(lif_file):
        print('Skipping...  %s' % fname)
    else:
        doc = Document(fname, data_dir, lif_file, mta_file, top_file,
                       ner_file, sen_file, tex_file, wik_file)
        doc.write(os.path.join(data_dir, 'ela'))


class Document(object):

    def __init__(self, fname, data_dir, lif_file, mta_file,
                 top_file, ner_file, sen_file, tex_file, wik_file):

        """Build a single LIF object with all relevant annotations. The annotations
        themselves are stored in the Annotations object in self.annotations."""
        self.id = int(os.path.split(fname)[0])
        self.fname = fname
        self.data_dir = data_dir
        self.lif = Container(lif_file).payload
        self.meta = LIF(mta_file)
        self.wikis = LIF(wik_file).metadata['wikified_es']
        self._add_views(ner_file, sen_file, tex_file, top_file)
        self.lif.metadata["filename"] = self.fname
        self.lif.metadata["year"] = self._get_year()
        self.annotations = Annotations(self.id, fname, doc=self,
                                       text=self.lif.text.value)
        self.annotations.text = self.lif.text.value
        self._collect_allowed_offsets()
        self._collect_annotations()

    def _add_views(self, ner_file, sen_file, tex_file, top_file):
        self._add_view("ner", ner_file, 1)
        self._add_view("sen", sen_file, 0)
        self._add_view("tex", tex_file, 0)
        self._add_view("top", top_file, 0)

    def _add_view(self, identifier, fname, view_rank):
        """Load fname as either a LIF object or a Container object and select the
        specified view, indicated by an index in the view list. Add the
        identifier to this view and add it to the list of views. Note that some
        files contain LIF objects and others contain Containers with LIF
        embedded. The view we are looking for is the first or second, depending
        on how the processor for those data was set up."""
        try:
            view = Container(fname).payload.views[view_rank]
        except KeyError:
            view = LIF(fname).views[view_rank]
        view.id = identifier
        self.lif.views.append(view)

    def _get_title(self):
        """We have no document structure and no metadata so just return None."""
        return None

    def _get_year(self):
        return self.meta.metadata["year"]

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
        #self._collect_sentences()
        self._collect_technologies()
        self._collect_entities()

    def _collect_authors(self):
        """Just get the authors from the metadata and put them in the index."""
        self.annotations.authors = self.meta.metadata['authors']

    def _collect_topics(self):
        """Collect the topics and put them on a list in the index."""
        view = self.get_view("top")
        for annotation in view.annotations:
            if annotation.type.endswith('SemanticTag'):
                topic_name = annotation.features['topic_name']
                self.annotations.topics.append(topic_name)
                for topic_element in topic_name.split():
                    self.annotations.topic_elements.append(topic_element)
        self.annotations.topic_elements = sorted(set(self.annotations.topic_elements))

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
                if NAMES.filter(entity.text):
                    continue
                # NAMES.normalize(entity.text)
                self.annotations.persons.add(entity)
            elif category == 'location':
                coordinates = LOCATIONS.get_coordinates(entity.text)
                entity.features['coordinates'] = coordinates
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

    def write(self, dirname):
        self.annotations.write(os.path.join(dirname, "%06d.json" % self.id),
                               self.lif.metadata["year"])

    def pp(self, prefix=''):
        views = ["%s:%d" % (view.id, len(view)) for view in self.lif.views]
        print("%s<Document id=%s '%s'>" % (prefix, self.id, self.fname))
        print("    <Views %s>" % ' '.join(views))
        print("    %s\n" % self.annotations)


class Annotations(object):

    """Object that holds all annotations for a file as well as the text of the
    document. Annotations include (1) metadata like authors and topics, which
    are not associated with offsets, (2) entities and events, which all are
    associated with text positions, and (3) relations, which currently have a
    special status in that they are the only complex annotation."""

    def __init__(self, docid, fname, doc=None, text=None):
        self.docid = docid
        self.fname = fname
        self.doc = doc
        self.text = text
        self.authors = []
        self.year = None
        self.wikis = doc.wikis
        self.wiki1 = doc.wikis[0]
        self.topics = []
        self.topic_elements = []
        self.sentences = []
        self.text = None
        self.technologies = IndexedAnnotations(doc, "technologies")
        self.persons = IndexedAnnotations(doc, "persons")
        self.organizations = IndexedAnnotations(doc, "organizations")
        self.locations = IndexedAnnotations(doc, "locations")

    def __str__(self):
        return "<Index %s %s>" % (self.docid, self.count_string())

    def count_string(self):
        return "tech:%d person:%d loc:%d org:%d event:%d time:%d rel:%d top:%d" \
            % (len(self.technologies), len(self.persons), len(self.locations),
               len(self.organizations), len(self.events), len(self.times),
               len(self.relations), len(self.topics))

    def _get_pages(self):
        # what a hack job...
        # well, as long as pdfinfo is there it is fine, we could glob the page
        # files and get the largest number (actually, that is only possible if
        # we hand in the directory of all sources, would also be hackish if we
        # hard code that).
        pdfinfo_fname = PDFINFO_FILE_PATTERN % self.docid
        if os.path.exists(pdfinfo_fname):
            with open(pdfinfo_fname, 'r') as pdfinfo_f:
                for line in pdfinfo_f:
                    if line.startswith('Pages:'):
                        return line.split()[1]
        else:
            return -1

    def write(self, fname, year=None):
        """Writes the document with the search fields to a json file."""
        json_object = {
            "text": self.text,
            "docid": self.docid,
            "docname": self.fname,
            "!url_pdf": "%s:8181/data/%s/pdf.pdf" % (TARSKI_URL, self.docid),
            "!url_tes": "%s:8181/data/%s/tesseract.txt" % (TARSKI_URL, self.docid),
            "!url_cover": "%s:5100/query/%s_0001.png" % (TARSKI_URL, self.docid),
            # "!url_pdf": f"http://tarski.cs-i.brandeis.edu:8181/data/{self.docid}/pdf.pdf",
            # "!url_cover": f"http://tarski.cs-i.brandeis.edu:5100/query/{self.docid}_0001.png",
            "ground_best": self.wiki1['title'],
            "ground_more": [w['title'] for w in self.wikis],
            "ori_pages": self._get_pages(),
            "year": year,
            "author": self.authors,
            "topic": self.topics,
            "topic_element": self.topic_elements,
            "technology": self.technologies.get_condensed_annotations(),
            "person": self.persons.get_condensed_annotations(),
            "location": self.locations.get_condensed_annotations(),
            "organization": self.organizations.get_condensed_annotations()
        }
        with open(fname, 'w', encoding='utf8') as fh:
            fh.write(json.dumps(json_object, sort_keys=True, indent=4))

    def pp(self, indent=''):
        print("%s%s\n" % (indent, self))


class IndexedAnnotations(object):

    """An index of all annotation in a file for a particular type (like "person" or
    "technology). Keeps the size, the list of annotations, a set of text strings
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
        # TODO: filter is disabled because it is not clear whether we should
        # ignore named entities in crap sentences.
        # self._filter_annotations()
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

    def get_condensed_annotations(self):
        """Returns a list of dictionaries where each dictionary has two keys:
        'text' and 'offsets', the latter is string with start-end pairs like
        "1641-1649 4786-4794"."""
        annos = {}
        for anno in self.annotations:
            offsets = "%s-%s" % (anno.start, anno.end)
            obj = {"text": anno.text, "offsets": offsets}
            # TODO: a bit hackish, but needed to deal with coordinates, which
            # are the only feature we preserve for the index -- refactor this
            coordinates = anno.features.get('coordinates')
            if coordinates is not None:
                obj['coordinates'] = coordinates
            # TODO: also a bit hackish, but we need to get the text right for
            # technologies with normalized names
            normalized_name = anno.features.get('term_normalized')
            if normalized_name is not None:
                anno.text = normalized_name
            annos.setdefault(anno.text, []).append(obj)
        answer = []
        for anno in annos:
            instances = annos[anno]
            offsets = ' '.join([inst['offsets'] for inst in instances])
            obj =  {"text": anno, "offsets": offsets}
            # TODO: see comment above
            if "coordinates" in instances[0]:
                obj["coordinates"] = instances[0]['coordinates']
            answer.append(obj)
        return answer

    def get_index(self):
        return self.idx_p1_p2_id

    def print_annotations_index(self):
        print(self.type)
        for text in sorted(self.idx_text_offsets):
            print("  %s  %s" % (text.replace('\n', '<S>'),
                                self.idx_text_offsets[text]))

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

    data_dir, filelist, start, end, crash = get_options()
    create_documents(data_dir, filelist, start, end, crash=crash)
