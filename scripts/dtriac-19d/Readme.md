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
