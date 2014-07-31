import os
# pylint: disable=E0611
import distutils.ccompiler
import distutils.sysconfig
import data_dir

PYTHON_HEADERS = distutils.sysconfig.get_python_inc()
PYTHON_VERSION = distutils.sysconfig.get_python_version()
PYTHON_LIB = "python%s" % PYTHON_VERSION

OUTPUT_DIR = os.path.dirname(__file__)

SOURCES = [os.path.join(OUTPUT_DIR, f) for f in ['passfd.c']]
SHARED_OBJECT = '_passfd.so'


def passfd_setup(output_dir=OUTPUT_DIR):
    '''
    Compiles the passfd python extension.

    :param output_dir: where the _passfd.so module will be saved
    :return: None
    '''
    if output_dir is None:
        output_dir = OUTPUT_DIR

    output_file = os.path.join(output_dir, SHARED_OBJECT)

    c = distutils.ccompiler.new_compiler()
    distutils.sysconfig.customize_compiler(c)
    objects = c.compile(SOURCES, include_dirs=[PYTHON_HEADERS],
                        output_dir=data_dir.get_tmp_dir(),
                        extra_postargs=['-fPIC'])
    c.link_shared_object(objects, output_file, libraries=[PYTHON_LIB])


def import_passfd():
    '''
    Imports and lazily sets up the passfd module

    :return: passfd module
    '''
    try:
        import passfd
    except ImportError:
        passfd_setup()
        import passfd

    return passfd


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        passfd_setup(sys.argv[1])
    else:
        passfd_setup()
