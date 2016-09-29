# -*- coding: utf-8 -*-

import errno
import os
import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
root_path = os.path.abspath(os.path.join("..", ".."))
sys.path.insert(0, root_path)

from avocado.utils import path
from avocado.utils import process

# Flag that tells if the docs are being built on readthedocs.org
ON_RTD = os.environ.get('READTHEDOCS', None) == 'True'

#
# Auto generate API documentation
#
api_source_dir = os.path.join(root_path, 'avocado')
base_api_output_dir = os.path.join(root_path, 'docs', 'source', 'api')
try:
    apidoc = path.find_command('sphinx-apidoc')
    apidoc_template = apidoc + " -o %(output_dir)s " + api_source_dir + " %(exclude_dirs)s"
except path.CmdNotFoundError:
    apidoc = False

# Documentation sections. Key is the name of the section, followed by:
# Second level module name (after avocado), Module description,
# Output directory, List of directory to exclude from API  generation,
# list of (duplicated) generated reST files to remove (and avoid warnings)
API_SECTIONS = {"Test APIs": (None,
                              "This is the bare mininum set of APIs that users "
                              "should use, and can rely on, while writing tests.",
                              "test",
                              ("core", "utils", "plugins"),
                              ("modules.rst", )),

                "Utilities APIs": ("utils",
                                   "This is a set of utility APIs that Avocado "
                                   "provides as added value to test writers.",
                                   "utils",
                                   ("core", "plugins"),
                                   ("avocado.rst", "modules.rst"),),

                "Internal (Core) APIs": ("core",
                                         "Internal APIs that may be of interest to "
                                         "Avocado hackers.",
                                         "core",
                                         ("utils", "plugins"),
                                         ("avocado.rst", "modules.rst")),

                "Extension (plugin) APIs": ("plugins",
                                            "Extension APIs that may be of interest to "
                                            "plugin writers.",
                                            "plugins",
                                            ("core", "utils"),
                                            ("avocado.rst", "modules.rst"))}

# clean up all previous rst files. RTD is known to keep them from previous runs
process.run("find %s -name '*.rst' -delete" % base_api_output_dir)

for (section, params) in API_SECTIONS.iteritems():
    output_dir = os.path.join(base_api_output_dir, params[2])
    exclude_dirs = [os.path.join(api_source_dir, d)
                    for d in params[3]]
    exclude_dirs = " ".join(exclude_dirs)
    files_to_remove = [os.path.join(base_api_output_dir, output_dir, d)
                       for d in params[4]]
    # generate all rst files
    if apidoc:
        cmd = apidoc_template % locals()
        process.run(cmd)
        # remove unnecessary ones
        for f in files_to_remove:
            os.unlink(f)

    # rewrite first lines of main rst file for this section
    second_level_module_name = params[0]
    if second_level_module_name is None:
        main_rst = os.path.join(output_dir,
                                "avocado.rst")
    else:
        main_rst = os.path.join(output_dir,
                                "avocado.%s.rst" % second_level_module_name)
    if not apidoc:
        main_rst_content = []
        try:
            os.makedirs(os.path.dirname(main_rst))
        except OSError as details:
            if not details.errno == errno.EEXIST:
                raise
    else:
        main_rst_content = open(main_rst).readlines()

    new_main_rst_content = [section, "=" * len(section), "",
                            params[1], ""]
    new_main_rst = open(main_rst, "w")
    new_main_rst.write("\n".join(new_main_rst_content))
    new_main_rst.write("".join(main_rst_content[2:]))
    new_main_rst.close()

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.intersphinx',
              'sphinx.ext.todo',
              'sphinx.ext.coverage']

master_doc = 'index'
project = u'Avocado'
copyright = u'2014-2015, Red Hat'

version_file = os.path.join(root_path, 'VERSION')
VERSION = open(version_file, 'r').read().strip()
version = VERSION
release = VERSION

if not ON_RTD:  # only import and set the theme if we're building docs locally
    try:
        import sphinx_rtd_theme
        html_theme = 'sphinx_rtd_theme'
        html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
    except ImportError:
        html_theme = 'default'

htmlhelp_basename = 'avocadodoc'

latex_documents = [
    ('index', 'avocado.tex', u'avocado Documentation',
     u'Avocado Development Team', 'manual'),
]

man_pages = [
    ('index', 'avocado', u'avocado Documentation',
     [u'Avocado Development Team'], 1)
]

texinfo_documents = [
    ('index', 'avocado', u'avocado Documentation',
     u'Avocado Development Team', 'avocado', 'One line description of project.',
     'Miscellaneous'),
]

# Older python-sphinx cannot handle newer inventory files (objects.inv)
# this is not failproof, as there can be newer python-sphinx on older
# Python, but it seems to be good enough.
if sys.version_info[0] == 2 and sys.version_info[1] == 6:
    intersphinx_python_url = 'http://docs.python.org/2.6/'
else:
    intersphinx_python_url = 'http://docs.python.org/'
intersphinx_mapping = {intersphinx_python_url: None}

autoclass_content = 'both'
