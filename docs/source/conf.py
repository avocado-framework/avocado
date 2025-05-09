# -*- coding: utf-8 -*-
"""This is used as config file to generate Avocado's documentation."""

import errno
import importlib
import os
import sys

from avocado.core import parameters
from avocado.core.varianter import Varianter
from avocado.utils import genio  # pylint: disable=C0413
from avocado.utils import path  # pylint: disable=C0413
from avocado.utils import process  # pylint: disable=C0413

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
ROOT_PATH = os.path.abspath(os.path.join("..", ".."))
sys.path.insert(0, ROOT_PATH)


#
# Auto generate API documentation
#
API_SOURCE_DIR = os.path.join(ROOT_PATH, "avocado")
BASE_API_OUTPUT_DIR = os.path.join(ROOT_PATH, "docs", "source", "api")
try:
    APIDOC = path.find_command("sphinx-apidoc")
    APIDOC_TEMPLATE = APIDOC + " -o %(output_dir)s %(API_SOURCE_DIR)s %(exclude_dirs)s"
except path.CmdNotFoundError:
    APIDOC = False


def generate_reference():
    avocado = os.path.join(API_SOURCE_DIR, "__main__.py")
    result = process.run(f"{sys.executable} {avocado}  config reference")
    reference_path = os.path.join(
        ROOT_PATH, "docs", "source", "config", "reference.rst"
    )
    stdout_text = result.stdout_text.replace("['/run/*']", r"['/run/\*']")
    with open(reference_path, "w", encoding="utf-8") as reference:
        reference.write(stdout_text)


def generate_vmimage_distro():
    yaml_path = [
        os.path.join(
            ROOT_PATH,
            "selftests",
            "vmimage",
            "variants",
            "vmimage.py.data",
            "variants.yml",
        )
    ]
    reference_dir_path = os.path.join(
        ROOT_PATH, "docs", "source", "guides", "writer", "libs", "data", "vmimage"
    )
    reference_path = os.path.join(reference_dir_path, "supported_images.csv")

    config = {"yaml_to_mux.files": yaml_path, "yaml_to_mux.inject": []}
    varianter = Varianter()
    varianter.parse(config)

    try:
        os.makedirs(reference_dir_path)
    except FileExistsError:
        pass

    with open(reference_path, "w", encoding="utf-8") as reference:
        reference.write("Provider, Version, Architecture\n")
        for v in varianter.itertests():
            vmimage_params = parameters.AvocadoParams(v["variant"], ["/run/*"])
            vmimage_name = vmimage_params.get("name")
            vmimage_version = vmimage_params.get("version")
            vmimage_arch = vmimage_params.get("arch", path="*/architectures/*")
            distro_arch_path = f"/run/distro/{vmimage_name}/{vmimage_arch}/*"
            vmimage_arch = vmimage_params.get(
                "arch", path=distro_arch_path, default=vmimage_arch
            )
            reference.write(
                f"{str(vmimage_name)},{str(vmimage_version)}," f"{str(vmimage_arch)}\n"
            )


generate_reference()
generate_vmimage_distro()

# Documentation sections. Key is the name of the section, followed by:
# Second level module name (after avocado), Module description,
# Output directory, List of directory to exclude from API  generation,
# list of (duplicated) generated reST files to remove (and avoid warnings)
# References tag
API_SECTIONS = {
    "Test APIs": (
        None,
        genio.read_file("api/headers/test"),
        "test",
        ("core", "utils", "plugins"),
        ("modules.rst",),
        ".. _tests-api-reference:\n",
    ),
    "Utilities APIs": (
        "utils",
        genio.read_file("api/headers/utils"),
        "utils",
        ("core", "plugins"),
        ("avocado.rst", "modules.rst"),
        "",
    ),
    "Internal (Core) APIs": (
        "core",
        genio.read_file("api/headers/core"),
        "core",
        ("utils", "plugins"),
        ("avocado.rst", "modules.rst"),
        "",
    ),
    "Extension (plugin) APIs": (
        "plugins",
        genio.read_file("api/headers/plugins"),
        "plugins",
        ("core", "utils"),
        ("avocado.rst", "modules.rst"),
        "",
    ),
}

# clean up all previous rst files. RTD is known to keep them from previous runs
process.run(f"find {BASE_API_OUTPUT_DIR} -name '*.rst' -delete")

for section, params in API_SECTIONS.items():
    output_dir = os.path.join(BASE_API_OUTPUT_DIR, params[2])
    exclude_dirs = [os.path.join(API_SOURCE_DIR, d) for d in params[3]]
    exclude_dirs = " ".join(exclude_dirs)
    files_to_remove = [
        os.path.join(BASE_API_OUTPUT_DIR, output_dir, d) for d in params[4]
    ]

    # generate all rst files
    if APIDOC:
        cmd = APIDOC_TEMPLATE % locals()
        process.run(cmd)
        # remove unnecessary ones
        for f in files_to_remove:
            os.unlink(f)
    # rewrite first lines of main rst file for this section
    second_level_module_name = params[0]
    if second_level_module_name is None:
        main_rst = os.path.join(output_dir, "avocado.rst")
    else:
        main_rst = os.path.join(output_dir, f"avocado.{second_level_module_name}.rst")
    if not APIDOC:
        main_rst_content = []
        try:
            os.makedirs(os.path.dirname(main_rst))
        except OSError as details:
            if details.errno != errno.EEXIST:
                raise
    else:
        with open(main_rst, encoding="utf-8") as main_rst_file:
            main_rst_content = main_rst_file.readlines()

    new_main_rst_content = [params[5], section, "=" * len(section), "", params[1], ""]
    with open(main_rst, "w", encoding="utf-8") as new_main_rst:
        new_main_rst.write("\n".join(new_main_rst_content))
        new_main_rst.write("".join(main_rst_content[2:]))

# Generate optional-plugins
OPTIONAL_PLUGINS_PATH = os.path.join(ROOT_PATH, "optional_plugins")
API_OPTIONAL_PLUGINS_PATH = os.path.join(BASE_API_OUTPUT_DIR, "optional-plugins")
if not os.path.exists(API_OPTIONAL_PLUGINS_PATH):
    os.makedirs(API_OPTIONAL_PLUGINS_PATH)
with open(
    os.path.join(API_OPTIONAL_PLUGINS_PATH, "index.rst"), "w", encoding="utf-8"
) as optional_plugins_toc:
    optional_plugins_toc.write(
        """.. index file for optional plugins API

====================
Optional Plugins API
====================

The following pages document the private APIs of optional Avocado plugins.

.. toctree::
   :maxdepth: 1

    """
    )
    for path in next(os.walk(OPTIONAL_PLUGINS_PATH))[1]:
        name = f"avocado_{os.path.basename(path)}"
        try:
            importlib.import_module(name)
        except ImportError:
            continue

        path = os.path.join(OPTIONAL_PLUGINS_PATH, path, name)
        if not os.path.exists(path):
            continue
        output_dir = os.path.join(API_OPTIONAL_PLUGINS_PATH, name)
        params = {"API_SOURCE_DIR": path, "output_dir": output_dir, "exclude_dirs": ""}
        process.run(f"{APIDOC_TEMPLATE % params} --implicit-namespaces")
        # Remove the unnecessary generated files
        os.unlink(os.path.join(output_dir, "modules.rst"))
        optional_plugins_toc.write(f"\n   {os.path.join(name, name)}")

extensions = [
    "sphinx.ext.autodoc",  # pylint: disable=C0103
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx_rtd_theme",
]

master_doc = "index"  # pylint: disable=C0103
project = "Avocado"  # pylint: disable=C0103
copyright = "2014-2023, Red Hat"  # pylint: disable=W0622,C0103

VERSION_FILE = os.path.join(ROOT_PATH, "VERSION")
VERSION = genio.read_file(VERSION_FILE).strip()
version = VERSION  # pylint: disable=C0103
release = VERSION  # pylint: disable=C0103

html_theme = "sphinx_rtd_theme"  # pylint: disable=C0103

htmlhelp_basename = "avocadodoc"  # pylint: disable=C0103

latex_documents = [  # pylint: disable=C0103
    (
        "index",
        "avocado.tex",
        "avocado Documentation",
        "Avocado Development Team",
        "manual",
    ),
]

man_pages = [  # pylint: disable=C0103
    ("index", "avocado", "avocado Documentation", ["Avocado Development Team"], 1)
]

texinfo_documents = [  # pylint: disable=C0103
    (
        "index",
        "avocado",
        "avocado Documentation",
        "Avocado Development Team",
        "avocado",
        "One line description of project.",
        "Miscellaneous",
    ),
]

intersphinx_mapping = {"python": ("https://docs.python.org", None)}

autoclass_content = "both"  # pylint: disable=C0103
