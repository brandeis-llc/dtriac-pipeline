"""create_lif.py

Create LIF files from the Science Parse output.

Usage:

$ python create_lif.py JSON_DIR LIF_DIR TXT_DIR

The first directory is the one with JSON files created by science parse, the
second the target for LIF files and the third the target for TXT files.

Should work for both Python2 and Python3.

"""


import os
import sys
import shutil
import codecs
import json
import pprint

from collections import Counter

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from lif import LIF, Container, View, Annotation


def read_sample(fname):
    extension = '.pdf.json.txt'
    fnames = [fname.strip() for fname in codecs.open(fname).readlines()]
    fnames = set([fname[:-len(extension)] for fname in fnames])
    return fnames


def get_files(fnames, directory, extension):
    files = {}
    for fname in sorted(os.listdir(directory)):
        stripped_fname = fname[:-len(extension)]
        if stripped_fname in fnames:
            files[stripped_fname] = os.path.join(directory, fname)
    if len(fnames) != len(files):
        print("WARNING: unexpected number of files found")
    return files


def copy_files_to_sample(json_files, target_dir):
    extension = '.pdf.json'
    print("Copying files to {}".format(target_dir))
    for json_file in json_files.values():
        target_file = os.path.basename(json_file)[:-len(extension)] + '.json'
        print("... {}".format(target_file))
        target_file = os.path.join(target_dir, target_file)
        shutil.copyfile(json_file, target_file)


def create_lif_files(science_parse_dir, lif_dir, txt_dir, test=False):
    for fname in os.listdir(science_parse_dir):
        create_lif_file(os.path.join(science_parse_dir, fname),
                        os.path.join(lif_dir, fname[:-5] + '.lif'),
                        os.path.join(txt_dir, fname[:-5] + '.txt'),
                        test)


def create_lif_file(json_file, lif_file, txt_file, test=False):
    print("Creating {}".format(lif_file))
    with codecs.open(json_file, encoding='utf8') as fh_in, \
         codecs.open(lif_file, 'w', encoding='utf8') as fh_out_lif, \
         codecs.open(txt_file, 'w', encoding='utf8') as fh_out_txt:
        json_obj = json.loads(fh_in.read())
        lif_obj = LIF()
        _add_metadata(lif_obj, json_obj)
        _add_view(lif_obj, json_obj)
        _add_rest(lif_obj, json_obj)
        container = Container()
        container.discriminator = "http://vocab.lappsgrid.org/ns/media/jsonld#lif"
        container.payload = lif_obj
        fh_out_lif.write(json.dumps(container.as_json(), indent=4))
        fh_out_txt.write(container.payload.text.value)
    if test:
        test_lif_file(lif_file)


def _add_metadata(lif_obj, json_obj):
    lif_obj.metadata['id'] = json_obj['id']
    lif_obj.metadata['authors'] = json_obj['authors']
    lif_obj.metadata['title'] = json_obj.get('title')
    lif_obj.metadata['year'] = json_obj.get('year')
    lif_obj.metadata['references'] = json_obj['references']
    

def _add_view(lif_obj, json_obj):
    view = View()
    lif_obj.views.append(view)
    view.id = "structure"
    view.metadata['contains'] = { vocab("Title"): {}, vocab("Abstract"): {},
                                  vocab("Section"): {}, vocab("Header"): {} }


def _add_rest(lif_obj, json_obj):
    text_value = StringIO()
    offset = 0
    annotations = lif_obj.views[0].annotations
    offset = _add_annotation(annotations, text_value, 'Title', json_obj.get('title'), offset)
    offset = _add_annotation(annotations, text_value, 'Abstract', json_obj.get('abstractText'), offset)
    for section in json_obj['sections']:
        offset = _add_annotation(annotations, text_value, 'Header', section.get('heading'), offset)
        offset = _add_annotation(annotations, text_value, 'Section', section.get('text'), offset)
    lif_obj.text.value = text_value.getvalue()


def _add_annotation(annotations, text_value, annotation_type, text, offset):
    if text is None:
        return offset
    prefix = None
    if annotation_type in ('Title', 'Abstract'):
        prefix = annotation_type.upper()
    if prefix is not None:
        anno = {
            "id": IdentifierFactory.next_id('Header'),
            "@type": vocab('Header'),
            "start": offset,
            "end": offset + len(prefix) } 
        annotations.append(Annotation(anno))
        text_value.write(prefix + u"\n\n")
        offset += len(prefix) + 2
    anno = {
        "id": IdentifierFactory.next_id(annotation_type),
        "@type": vocab(annotation_type),
        "start": offset,
        "end": offset + len(text) } 
    annotations.append(Annotation(anno))
    text_value.write(text + u"\n\n")
    return offset + len(text) + 2


def test_lif_file(lif_file):
    """Just print the text of all headers, should give an indication of whether all
    the offsets are correct."""
    lif = Container(json_file=lif_file).payload
    text = lif.text.value
    view = lif.views[0]
    for anno in view.annotations:
        if anno.type.endswith('Header'):
            print("[{}]".format(text[anno.start:anno.end]))
    print('')


class IdentifierFactory(object):
    
    ids = { 'Title': 0, 'Abstract': 0, 'Header': 0, 'Section': 0 }

    @classmethod
    def next_id(cls, tagname):
        cls.ids[tagname] += 1
        return "{}{:04d}".format(tagname.lower(), cls.ids[tagname])


def vocab(annotation_type):
    return "http://vocab.lappsgrid.org/{}".format(annotation_type)

        
if __name__ == '__main__':

    # One off code to add the 25 files from the sample to samples/small-25-json
    if False:
        repo = '/Users/marc/Desktop/projects/dtra/dtra-534'
        science_parse_full_dir = '../spv1-results'
        science_parse_sample_dir = '../samples/small-25-json'
        fnames = read_sample('../sample-files.txt')
        json_files = get_files(fnames, science_parse_full_dir, '.pdf.json')
        copy_files_to_sample(json_files, science_parse_sample_dir)

    science_parse_dir = sys.argv[1]
    lif_dir = sys.argv[2]
    txt_dir = sys.argv[3]
    create_lif_files(science_parse_dir, lif_dir, txt_dir, test=False)
