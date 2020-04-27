class Pair:

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __str__(self):
        return str(self.name) + " != " + str(self.value)

    def __eq__(self, other):
        return self.name == other.name and self.value == other.value

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.__str__())
