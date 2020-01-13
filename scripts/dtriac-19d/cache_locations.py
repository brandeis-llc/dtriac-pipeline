"""cache_locations.py

Caching locations using the Nominatum GeoEncoder.

Somewhat of a stop gap because it took too long to figure out the Google
geonames interface. Could also use geopy with GoogleV3 instead of Nominatum, but
that requires registration.

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

Usage:

$ python3 cache_locations LIMIT

This looks up all locations that occur less or equal than MAX_COUNT times and
more or equal than MIN_COUNT times. Use LIMIT when testing the script to avoid
repeated queries.

TODO: first time I ran this on just those locations that occur 10 times or more
in LOCATIONS_FILE, may want to do this later for those that ocuur 5-9 times.

"""

import sys
import time
import json

from geopy.geocoders import Nominatim


GEOLOCATOR = Nominatim()

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


if __name__ == '__main__':
    output = sys.argv[1]
    limit = int(sys.argv[2])
    process_locations(output, limit)
