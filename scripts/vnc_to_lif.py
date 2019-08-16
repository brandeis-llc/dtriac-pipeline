import os
import re
import sys
from sys import argv
from lif import LIF, Annotation, View, Container

def generate_lif(txt, vnc):
    """
    * txt is a plain text file only with the original text value. 
    * vnc (verbnetclass) is a output from clearwsd file (mostly in conll format)
    This function will generate a LIF json file using disambiguation annotation 
    encoded in the vnc file, using txt as top-level `text` field. 
    """
    t = open(txt, encoding="utf-8")
    v = open(vnc, encoding="utf-8")
    lif_obj = LIF()
    cont_obj = Container()
    cont_obj.discriminator = "http://vocab.lappsgrid.org/ns/media/jsonld#lif"
    cont_obj.payload = lif_obj

    raw_text = t.read()
    t.close()
    lif_obj.text.value = raw_text

    vnc_view = View()
    lif_obj.views.append(vnc_view)
    vnc_view.id = "verbnettag"
    vnc_view.metadata['contains'] = { vocab('SemanticTag'): {}}

    annotations = [line for line in v if line.startswith('#')]
    v.close()
    for annotation in annotations:
        _, oid, osent, otoken, olemma, olabel = annotation.split('\t')[0].split()
        s, e = map(int, re.match(r'\d+\[(\d+),(\d+)\]', otoken).groups())
        ann = {}
        ann["id"] = "vnc_" + oid
        ann["start"] = s
        ann["end"] = e
        ann["@type"] = vocab("SemanticTag")
        ann["features"] = { "tags": [olabel], "type": "VerbNetClass",
                "lemma": olemma, "text": raw_text[s:e]}
        ann_obj = Annotation(ann)
        vnc_view.annotations.append(ann_obj)
    cont_obj.write()



def vocab(annotation_type):
    return "http://vocab.lappsgrid.org/%s" % annotation_type

if __name__ == "__main__":
    txtfile = argv[1]
    vncfile = argv[2]
    generate_lif(txtfile, vncfile)
