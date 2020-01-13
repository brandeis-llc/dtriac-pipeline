
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

    def filter(self, name):
        # common first names and Jr and Sr are filtered
        if (name.lower() in self.names_to_filter
            or name in ('Jr', 'Jr.', 'Sr', 'Sr.')):
            return True
        # names that end with "Road" are not names
        if name.endswith(' Road'):
            return True
        # all intials is either a location or a part of a name
        if self.initials_only(name):
            return True
        return False

    @staticmethod
    def initials_only(name):
        for part in name.split():
            if not (len(part) == 2 and part[1] == '.'):
                return False
        return True
