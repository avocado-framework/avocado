Subclassing Avocado
===================

Subclassing Avocado Test class to extend its features is quite straight forward
and it might constitute a very useful resource to have some shared/recurrent
code hosted in your project repository.

In this section we propose an project organization that will allow you to
create and install your so called sub-framework.

Let's use, as an example, a project called Apricot Framework. Here's the
proposed filesystem structure::

    ~/git/apricot (master)$ tree
    .
    ├── apricot
    │   ├── __init__.py
    │   └── test.py
    ├── README.rst
    ├── pyproject.toml
    ├── tests
    │   └── test_example.py
    └── VERSION

- ``pyproject.toml``: In the ``pyproject.toml`` it is important to specify the
  ``avocado-framework`` package as a dependency::

    [build-system]
    requires = ["setuptools>=61.0", "wheel"]
    build-backend = "setuptools.build_meta"

    [project]
    name = "apricot"
    dynamic = ["version"]
    description = "Apricot - Avocado SubFramework"
    authors = [
        {name = "Apricot Developers", email = "apricot-devel@example.com"},
    ]
    dependencies = [
        "avocado-framework",
    ]

    [tool.setuptools]
    packages = ["apricot"]

    [tool.setuptools.dynamic]
    version = {file = "VERSION"}


- ``VERSION``: Version your project as you wish::

    1.0

- ``apricot/__init__.py``: Make your new test class available in your module
  root::

    __all__ = ['ApricotTest']

    from apricot.test import ApricotTest


- ``apricot/test.py``: Here you will be basically extending the Avocado Test
  class with your own methods and routines::

    from avocado import Test

    class ApricotTest(Test):
        def setUp(self):
            self.log.info("setUp() executed from Apricot")

        def some_useful_method(self):
            return True



- ``tests/test_example.py``: And this is how your test will look like::

    from apricot import ApricotTest

    class MyTest(ApricotTest):
        def test(self):
            self.assertTrue(self.some_useful_method())



To (non-intrusively) install your module, use::

    ~/git/apricot (master)$ pip install -e . --user
    Obtaining file:///home/user/git/apricot
      Installing build dependencies ... done
      Checking if build backend supports build_editable ... done
      Getting requirements to build editable ... done
      Preparing editable metadata ... done
    Requirement already satisfied: avocado-framework in /home/user/.local/lib/python3.11/site-packages (from apricot==1.0) (112.0)
    Building wheels for collected packages: apricot
      Building editable for apricot (pyproject.toml) ... done
      Created wheel for apricot: filename=apricot-1.0-py3-none-any.whl
      Stored in directory: /tmp/pip-ephem-wheel-cache
    Successfully built apricot
    Installing collected packages: apricot
    Successfully installed apricot-1.0

And to run your test::

    ~/git/apricot$ avocado run tests/test_example.py
    JOB ID     : 02c663eb77e0ae6ce67462a398da6972791793bf
    JOB LOG    : $HOME/avocado/job-results/job-2017-11-16T12.44-02c663e/job.log
        (1/1) tests/test_example.py:MyTest.test: STARTED
        (1/1) tests/test_example.py:MyTest.test: PASS (0.03 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 0.95 s
    JOB HTML   : $HOME/avocado/job-results/job-2017-11-16T12.44-02c663e/results.html
