# Pipeline for dtriac-19d

Data are on tarski in `/data/dtriac/dtriac-19d/all`, which has the results of the raw Tesseract processing. In that directory there are about 15K directories, each a number, and all of them contain a file named `tesseract-300dpi-20p.txt` which has the OCR results of the first 20 pages.

Results of language processing to be written to  `/data/dtriac/dtriac-19d/all-processed`.

The two file lists were created as follows:

```bash
$ find /data/dtriac/dtriac-19d/all | grep tesseract- | cut -d'/' -f6- > files-sorted.txt
$ sort -R files-sorted.txt > files-random.txt
```

## Creating LIF files

Use the `create_lif.py` script in this directory.

```bash
$ python3 create_lif -s /data/dtriac/dtriac-19d/all \
                     -d /data/dtriac/dtriac-19d/all-processed \
                     -f files-random.txt \
                     -e 99999
```

This will process all document (since 99999 is bigger than the total number) and write results to `/data/dtriac/dtriac-19d/all-processed`.

Note that this imports some code that intends to run on both Python2 and Python 3 and that includes calls to the `past` package so you may need to install that with `pip3 install future`.


## Running the topic model

You need to install `gensim` and `nltk` and for the latter you need to load a few resources:

```python
>>> nltk.download('stopwords')
>>> nltk.download('punkt')
>>> nltk.download('wordnet')
```

Building the model:

```bash
$ python3 generate_topics.py --build \
    -d /data/dtriac/dtriac-19d/all-processed \
    -f files-random.txt -e 100
```

Here we build a model using the first 100 files listed in `files-random.txt`, taking them from `/data/dtriac/dtriac-19d/all-processed/lif`.

This needs to be done only once. The model itself is saved in `topics/` and will be loaded as needed.

Running the model on LIF files:

```bash
$ python3 generate_topics.py -d DATA_DIR -f FILELIST -e 16000
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
