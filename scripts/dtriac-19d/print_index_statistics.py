"""print_index_statistics.py

Print statistics from the json files that will be imported into ES.

Best way to use:

$ python3 index_statistics.py -d <DATA_DIR> -e <INT> | grep -v 2020

The grep filters out the regular file-by-file printing (assuming it is still
2020 when you do this).

"""

import os
import json

from utils import get_options, process_list, ensure_directory


def show_statistics(data_dir, fname):
    subdir = int(os.path.split(fname)[0])
    ela_file = os.path.join(data_dir, 'ela', "%06d.json" % subdir)
    json_obj = json.load(open(ela_file))
    authors = len(json_obj.get('author', []))
    wikis = len(json_obj.get('ground_more', []))
    locations = len(json_obj.get('location', []))
    organizations = len(json_obj.get('organization', []))
    persons = len(json_obj.get('person', []))
    topics = len(json_obj.get('topic', []))
    print("%06d    a:%d\tt:%d\tw:%d\tl:%d\to:%s\tp:%d"
          % (subdir, authors, topics, wikis, locations, organizations, persons))


if __name__ == '__main__':

    data_dir, filelist, start, end, crash = get_options()
    process_list(data_dir, filelist, start, end, crash, show_statistics)
