#!/bin/bash

size="all"
size="25"

if [ "$size" = "all" ]; then
    repo=/DATA/dtra/dtra-534-full-annotated
    lif=$repo/spv1-results-lif
    ner=$repo/spv1-results-lif-ner
    rel=$repo/spv1-results-lif-rel
    tex=$repo/spv1-results-lif-tex
    ttk=$repo/spv1-results-lif-ttk
    sen=$repo/spv1-results-lif-sen
    vnc=$repo/spv1-results-lif-vnc
    top=$repo/spv1-results-lif-top
    ela=$repo/spv1-results-lif-ela
else
    repo=..
    lif=$repo/samples/small-25-lif
    ner=$repo/samples/small-25-ner
    tex=$repo/samples/small-25-tex
    ttk=$repo/samples/small-25-ttk
    sen=$repo/samples/small-25-sen
    rel=$repo/samples/small-25-rel
    vnc=$repo/samples/small-25-vnc
    top=$repo/samples/small-25-top
    ela=$repo/samples/small-25-ela
fi

echo $ python3 create_index_docs.py $lif $ner $tex $ttk $sen $rel $vnc $top $ela
python3 create_index_docs.py $lif $ner $tex $ttk $sen $rel $vnc $top $ela
