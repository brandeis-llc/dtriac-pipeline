
repo=/Users/marc/Desktop/projects/dtra/dtra-534
#repo=/Users/marc/Documents/git/dtra/dtra-534

sample=$repo/sample-files.txt

lif=$repo/samples/small-25-lif
ner=$repo/samples/small-25-ner
tex=$repo/samples/small-25-tex
ttk=$repo/samples/small-25-ttk
rel=$repo/samples/small-25-rel

ela=$repo/samples/small-25-ela
#ela=$repo/samples/tmp

python create_index_docs.py $lif $ner $tex $ttk $rel $ela $sample
