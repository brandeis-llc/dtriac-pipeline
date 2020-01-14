import pickle


# pickled locations with coordinates, created by locations.py
LOCATIONS_INDEX = 'data/locations/locations.idx.pickle'

# list of common first names
FIRST_NAMES = 'data/names/common-first-names.txt'


class Names(object):

    def __init__(self):
        self.names_to_filter = set()
        for line in open(FIRST_NAMES):
            if line.startswith('#'):
                continue
            (rank, male, count1, female, count2) = line.strip().split('\t')
            self.names_to_filter.add(male.lower())
            self.names_to_filter.add(female.lower())

    @staticmethod
    def normalize(name):
        normalized = []
        for part in name.split():
            if part.isupper() and '.' not in part:
                normalized.append(part.capitalize())
            else:
                normalized.append(part)
        normalized = ' '.join(normalized)
        if name.replace('\n', '') != normalized:
            print("'%s' ==> '%s'" % (name, normalized))
        return normalized

    @staticmethod
    def split(lif, annotation):
        name = lif.text.value[annotation.start:annotation.end]
        if ('\n' in name
            and lif.text.value[annotation.start-1] == '\n'):
            #print('=', lif.text.value[annotation.end+1])
            for part in name.split('\n'):
                print('>', part)

    def filter(self, name):
        # common first names and Jr and Sr are filtered
        if (name.lower() in self.names_to_filter
            or name in ('Jr', 'Jr.', 'Sr', 'Sr.')):
            return True
        # names that end with "Road" are not names
        if name.endswith(' Road'):
            return True
        # hack to deal with 'John J. Kingman Road' spillovers, should use a more
        # global approach and collect prefixes of names with roads
        if name.lower() in ('john j.', 'john j. kingman'):
            # print(name)
            return True
        # all initials is either a location or a part of a name
        if self.initials_only(name):
            return True
        return False

    @staticmethod
    def initials_only(name):
        for part in name.split():
            if not (len(part) == 2 and part[1] == '.'):
                return False
        return True


class Locations(object):

    def __init__(self):
        self.data = pickle.load(open(LOCATIONS_INDEX, 'rb'))

    def get_coordinates(self, location):
        result = self.data.get(location)
        if result is None:
            return None
        return "%.2f,%.2f" % (float(result['lat']), float(result['lon']))
