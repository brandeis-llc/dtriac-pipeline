"""locations.py

Some utilities to manage locations.

- Caching locations using the Nominatum GeoEncoder.
- Creating a locations index from the cached locations

== Caching locations

$ python3 locations.py --cache OUTPUT_FILE LIMIT

This looks up all locations that occur less or equal than MAX_COUNT times and
more or equal than MIN_COUNT times. Use LIMIT when testing the script to avoid
repeated queries. Uses the Nominatum GeoEncoder which is somewhat of a stop gap
because it took too long to figure out the Google geonames interface. Could also
use geopy with GoogleV3 instead of Nominatum, but that requires registration.

The usage policy at https://operations.osmfoundation.org/policies/nominatim/
forbids heavy use. Some nuggets from the policy:

- Maximum of 1 request per second
- Cache results locally (repeated queries are flagged)

Requires installation of geopy (https://geopy.readthedocs.io/en/stable/).

>>> from geopy.geocoders import Nominatim
>>> geolocator = Nominatim()
>>> location = geolocator.geocode("175 5th Avenue NYC")
>>> print(location.address)
Flatiron Building, 175, 5th Avenue, Flatiron, New York, NYC, New York, ...
>>> print((location.latitude, location.longitude))
(40.7410861, -73.9896297241625)

Other descriptors available on the location object are altitude, point and
raw. The last of those is a json object that contains 'boundingbox', 'lat' and
'long' properties. The value of raw is what we are caching.

TODO: first time I ran this on just those locations that occur 10 times or more
in LOCATIONS_FILE, may want to do this later for those that occur 5-9 times.


== Creating locations index

$ python3 locations.py --create CACHE_FILE INDEX_FILE

Takes the file created in the --cache step and creates a much smaller version
of it with just the data we need and saved as a pickle file.

"""

import sys
import time
import json
import pickle

from geopy.geocoders import Nominatim


GEOLOCATOR = Nominatim(user_agent='cache_locations.py')

LOCATIONS_FILE = 'data/locations/locations.txt'

MAX_COUNT = 99999
MIN_COUNT = 10


def get_locations():
    for line in open(LOCATIONS_FILE):
        if line.startswith("#"):
            continue
        count, location = line.strip().split('\t')
        count = int(count.strip())
        yield (count, location)


def process_locations(outfile, limit):
    locations = {
        'time': time.time(),
        'producer': 'scripts/dtriac-19d/cache_locations.py',
        'maxcount': MAX_COUNT,
        'mincount': MIN_COUNT,
        'limit': limit,
        'locations': {}}
    locations_processed = 0
    for count, location in get_locations():
        if MIN_COUNT <= count <= MAX_COUNT:
            locations_processed += 1
            if locations_processed > limit:
                break
            sys.stdout.write("%04d  %05d  %s\n" % (limit, count, location))
            try:
                result = GEOLOCATOR.geocode(location)
            except:
                result = None
            time.sleep(1)
            if result is not None:
                result = result.raw
            locations['locations'][location] = result
    json.dump(locations, open(outfile, 'w'), indent=4)


def build_locations_index(cached_locations_file, locations_index):
    json_obj = json.load(open(cached_locations_file))
    print("Building index for %d locations" % len(json_obj['locations']))
    idx = {}
    locations_with_coordinates = 0
    for location in json_obj['locations']:
        idx[location] = None
        result = json_obj['locations'][location]
        if result is not None:
            # look up is quite liberal (for example, when you look up Bali you
            # may get Paris as the result) so require the found address to match
            # the query in some form
            address = result['display_name']
            address_parts = [p.strip() for p  in address.split(',')]
            if location.lower() == address_parts[0].lower():
                # print(location, '--', address)
                locations_with_coordinates += 1
                idx[location] = {
                    'lat': result['lat'],
                    'lon': result['lon'],
                    'box': result['boundingbox'] }
    pickle.dump(idx, open(locations_index, 'wb'))
    print("Done building index containing non-null data for %d locations"
          % locations_with_coordinates)
    print("Index file: %s" % locations_index)


if __name__ == '__main__':

    mode = sys.argv[1]
    if mode == '--cache':
        outfile = sys.argv[2]
        limit = int(sys.argv[3])
        process_locations(outfile, limit)
    elif mode == '--create':
        infile = sys.argv[2]
        outfile = sys.argv[3]
        build_locations_index(infile, outfile)

