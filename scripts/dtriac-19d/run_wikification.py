"""
Using ES-based wikification method (see https://github.com/brandeis-llc/dtriac-wikification/issues/8),
this script reads in a directory of LIF files and writes wikified LIF files.
(up-to) 10-best wikification is written in .payload.metadata.wikified_es.
"""
import os

from wikification.wikify import by_es
from os.path import join as pjoin

from lif import LIF, Container


def wikify_dir(in_d, wikifier):
    lif_d = pjoin(in_d, 'lif')
    wik_d = pjoin(in_d, 'wik')
    for node in os.listdir(lif_d):
        if node.isnumeric() and os.path.isdir(pjoin(lif_d, node)):
            out_d = pjoin(wik_d, node)
            os.makedirs(out_d, exist_ok=True)
            out_f = pjoin(out_d, f'{node}.wik.lif')
            wikify_lif(pjoin(lif_d, node, "tesseract-300dpi-20p.lif"), wikifier).write(fname=out_f, pretty=True)


def wikify_lif(in_f, wikifier):
    in_lif = Container(in_f).payload
    out_lif = LIF(json_object=in_lif.as_json())
    out_lif.views = []
    out_lif.metadata["wikified_es"] = wikifier.wikify(out_lif.text.value)
    return out_lif


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__
    )
    parser.add_argument(
        '-w ', '--wikiindex',
        action='store',
        nargs='?',
        help='Elasticsearch index of wikipedia articles'
    )
    parser.add_argument(
        '-i', '--indir',
        default='',
        action='store',
        nargs='?',
        help='Directory name where input LIF data live under `lif` subdir. '
    )
    # for testing
    parser.add_argument(
        '-f', '--file',
        default='',
        action='store',
        nargs='?',
        help=''
    )
    args = parser.parse_args()
    wikifier = by_es.WikifyByES(args.wikiindex)
    # test with a single file
    if len(args.file) > 0:
        print(wikify_lif(args.file, wikifier))
    else:
        wikify_dir(args.indir, wikifier)
