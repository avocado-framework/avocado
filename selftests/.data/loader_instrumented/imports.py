# docstrings, methods, imports... pylint: disable=C0111,R0903,C0411,E0611,C0412

# module imports
import parent1  # .names[0].name => parent1
# class imports
import parent7.Class7  # .names[0].name => parent7.Class7   # bad example pylint: disable=I,C,W,E
import path.parent2  # .names[0].name => path.parent2

from path import parent3  # .module => path; .names[0] => parent3
import parent4 as asparent4  # .names[0].asname => asparent4; .names[0].name => parent4
import path.parent5 as asparent5  # .names[0].asname => asparent5; .names[0].name => path.parent5
from path import parent6 as asparent6  # .module => path; .names[0].asname => asparent6; .names[0].name => path.parent6

from .path.parent8 import Class8  # .module = path.parent8; name[0].name = Class8
import parent9.Class9 as AsClass9  # .names[0].asname => AsClass9; .names[0].name => parent9.Class9   # bad example pylint: disable=I,C,W,E
from .path.parent10 import Class10 as AsClass10  # .module => path.parent10; .names[0].asname => AsClass10; .names[0].name => Class10


class Test1(parent1.Class1):
    pass


# We don't support multi-level imports
class NoTest2(path.parent2.Class2):
    pass


class Test3(parent3.Class3):
    pass


class Test4(asparent4.Class4):
    pass


class Test5(asparent5.Class5):
    pass


class Test6(asparent6.Class6):
    pass


# Incorrect syntax, check we don't crash
class NoTest7(parent7.Class7):
    pass


class Test8(Class8):
    pass


# Incorrect syntax, but detecting is more complicated than necessary
# as it should fail on load-time... Let's include it.
class Test9(AsClass9):
    pass


class Test10(AsClass10):
    pass
