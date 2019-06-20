#! /usr/bin/env python
import os
import sys
import json
import lif


def create_dict(lif_dir):
    """
    Create a verbnet class dictionary, given a directory of LIF json files
    The dictionary will record all verb instances annotated with
    "SemanticTag (type: VerbNetClass)" in *.lif files inside the directory.
    The dictionary will be printed out as a JSON string ito STDOUT.
    It is supposed to be used as an external resource for query expansion
    in the flask web app that interacts with elastic indices."
    """
    # Primary dictionary to store all verbnet classes found in the corpus.
    # Should look like;
    # { verb : set(vbclass1, vbclass2, ...) }
    # In most cases, only a single class is associated with a verb.
    # Also don't forget to add the lemma of a verb even the lemma form was never found in the corpus
    # so that a search query with the lemma form can refer to the verbnet class dict.
    verbnettags = {}

    for lif_filename in (f for f in os.listdir(lif_dir) if f.endswith(".lif")):
        cont = lif.Container(os.path.join(lif_dir, lif_filename), None, None)
        lif_obj = cont.payload
        for view in lif_obj.views:
            if view.id.startswith("verbnet") and "http://vocab.lappsgrid.org/SemanticTag" in view.metadata['contains']:
                for annotation in view.annotations:
                    text = annotation.features['text']
                    lemma = annotation.features['lemma']
                    vbc = annotation.features['tags'][0]
                    verbnettags.get(text, set()).add(vbc)
                    verbnettags.get(lemma, set()).add(vbc)
    print(json.dumps(verbnettags))


if __name__ == "__main__":
    lif_dir = sys.argv[1]
    create_dict(lif_dir)