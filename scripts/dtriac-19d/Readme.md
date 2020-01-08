# Pipeline for dtriac-19d

Data are on tarski in `/data/dtriac/dtriac-19d/all`, which has the results of the raw Tesseract processing. In that directory there are about 15K directories, each a number, and all of them contain a file named `tesseract-300dpi-20p.txt` which has the OCR results of the first 20 pages. Results of language processing are to be written to  `/data/dtriac/dtriac-19d/all-processed`. In the examples below we assume you have set the following two environment variables with the values reflecting the locations on tarski:

```bash
$ export SOURCE=/data/dtriac/dtriac-19d/all
$ export DATA=/data/dtriac/dtriac-19d/all-processed
```


The two file lists (`files-sorted.txt` and `files-random.txt`) have a list of all OCR-ed files in `/data/dtriac/dtriac-19d/all` and were created as follows:

```bash
$ find /data/dtriac/dtriac-19d/all | grep tesseract- | cut -d'/' -f6- > files-sorted.txt
$ sort -R files-sorted.txt > files-random.txt
```

The pdf browser at http://tarski.cs-i.brandeis.edu:8181/ is useful for reference. If you know the file identifier you can use it as in http://tarski.cs-i.brandeis.edu:8181/data/32297/pdf.pdf.


## Creating LIF files

Use the `create_lif.py` script in this directory.

```bash
$ python3 create_lif -s $SOURCE -d $DATA -f files-random.txt -e 99999
```

This will process all documents (since 99999 is bigger than the total number) and write results to `/data/dtriac/dtriac-19d/all-processed/lif`.

Note that this imports some code that was intended to run on both Python2 and Python 3 and that includes calls to the `past` package so you may need to install that with `pip3 install future`.


## Running the topic model

You need to install `gensim` and `nltk` and for the latter you need to load a few resources:

```python
>>> nltk.download('stopwords')
>>> nltk.download('punkt')
>>> nltk.download('wordnet')
```

Building the model:

```bash
$ python3 generate_topics.py --build -d $DATA -f files-random.txt -e 100
```

Here we build a model using the first 100 files listed in `files-random.txt`, taking them from `/data/dtriac/dtriac-19d/all-processed/lif`.

This needs to be done only once. The model itself is saved in `topics/` and will be loaded as needed.

Running the model on LIF files:

```bash
$ python3 generate_topics.py -d $DATA -f files-random.txt -e 16000
```


## Running the Tarsqi Toolkit

We run this partially for the events and times, but mostly for the sentence splitting in the preprocessing.

See https://github.com/tarsqi/ttk on how to install TTK, note that for our purposes here we do not need to install Mallet. We used the most recent commit on the develop branch as of Dec 18 2019 (commit 00c6a53).

When installing TTK with a current version of the TreeTagger a change needed to be made to `wrapper.py` in `components/preprocessing/` where on line 35 you need to used `english-utf8.par` instead of `english-utf8.par`.

Another issue is in Evita, where some error trapping needs to be added to `components/evita/main.py`, replacing

```python
if not node.checkedEvents:
    node.createEvent(imported_events=self.imported_events)
```

with

```python
if not node.checkedEvents:
    try:
        node.createEvent(imported_events=self.imported_events)
    except Exception as e:
        logger.error(str(e))
```

This was not an issue with running this on PubMed abstracts (the only previous use of this), but maybe those abstracts were just too short and well-behaved for issues to pop up. Without trapping this error somehow no output is created.

Once you have TTK installed first set the `PYTHONPATH` environment variable and have it point to where TTK is installed, for example:

```bash
$ export PYTHONPATH=/home/marc/tools/ttk
```

Now use the `run_tarsqi.py` script in a similar way as before with other modules:

```bash
$ python2 run_tarsqi.py -d DATA_DIR -f FILELIST -e 100
```

This does not run the full TTK pipeline, just the preprocessor and time and event extraction.

Note that TTK requires Python 2.7. One other difference is that unlike previous modules this module creates gzipped files. Without compression running this on the first 1000 files creates 151M of data, which translates to about 315G for the entire dataset. Compression reduces disk space usage by a factor 15.


## Technologies

This requires two steps at the moment, one is to create a technology ontology using legacy code and the other is to use this ontology to look up terms. For the first step you need the following repositories:

- https://github.com/techknowledgist/tgist-corpus-preparation
- https://github.com/techknowledgist/tFeatures
- https://github.com/techknowledgist/tgist-classifiers

The first has two scripts `dtriac/lif2txt.txt` and `dtriac/create_filelist.txt` where the first takes the LIF files and creates bare text files, use this if you don't already have those files in you `$DATA` directory. The second script creates the file list that is used by the technology code. Then you take the technology code in the `tFeatures` repository, updated with some functionality to run the code over raw text data (at least commit 7973f07 or later in the develop branch). I ran this on my desktop at home as follows. First setting a few environment variables

```bash
$ export FILES=/DATA/dtra/dtriac/dtriac-19d/files.txt
$ export CORPUS=/DATA/dtra/dtriac/dtriac-19d/corpus
```

The first points at the file list created with `dtriac/create_filelist.txt`, the second points at where technology preprocessing data are put.

Now you can do the basic processing:

```bash
$ cd code
$ python2 step1_init.py -f $FILES -c $CORPUS --source text
$ python2 step2_process.py -c $CORPUS -n 15349 --populate --verbose
$ python2 step2_process.py -c $CORPUS -n 15349 --xml2txt --verbose
$ python2 step2_process.py -c $CORPUS -n 15349 --txt2tag --verbose
$ python2 step2_process.py -c $CORPUS -n 15349 --tag2chk --verbose
```

Followed by the technology classifier, fist some environment variables

```bash
$ export CLASSIFICATION=/DATA/dtra/dtriac/dtriac-19d/classification
$ export MODEL=data/models/technologies-010-20140911/train.model
$ export MALLET=/Applications/ADDED/nlp/mallet/mallet-2.0.7/bin/
```

The first is where the results of the technology classification are saved, the second the location of the model and the third the location of Mallet. Use the `tgist-classifiers` repository (commit 82bce43 or later on the develop branch). Now you can run this (spread out over a few lines for readability):

```bash
$ python2 run_tclassify.py
    --classify
    --corpus $CORPUS
    --model $MODEL
    --output $CLASSIFICATION
    --mallet-dir $MALLET
```

For the second step (looking up ontology terms) you use the script `lookup.py`.

```bash
$ python3 lookup.py -d $DATA -f file-random.txt -e 99999
```

This looks up all technologies in the `technologies.txt` file in the tokenized and part-of-speech tagged data in `$DATA/pos`. The technologies file is part of the repository, but can be recreated with

```bash
$ python3 lookup --compile-technologies $CLASSIFICATION
```

The above uses the results from the technology classification.


## Creating the JSON documents for the index

Use the `create_index_docs.py` script in this directory.

```bash
$ python3 create_index_docs -d $DATA -f files-random.txt -e 99999
```

This script is a bit different from the other Python scripts in that it does not preserve the directory structure or the names of the files. It just dumps all files in `$DATA/ela` and uses names starting from `00001.json`.

Once you have create these documents you can load them into the index with

```bash
$ python3 load_index dtriac-19d $DATA/ela
```

This assume that an Elasticsearch instance is running on localhost on port 9200 and that it contains an index named `dtriac-19d`.
