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
    ├── setup.py
    ├── tests
    │   └── test_example.py
    └── VERSION

- ``setup.py``: In the ``setup.py`` it is important to specify the
  ``avocado-framework`` package as a dependency::

    from setuptools import setup, find_packages

    setup(name='apricot',
          description='Apricot - Avocado SubFramwork',
          version=open("VERSION", "r").read().strip(),
          author='Apricot Developers',
          author_email='apricot-devel@example.com',
          packages=['apricot'],
          include_package_data=True,
          install_requires=['avocado-framework']
          )


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

    ~/git/apricot (master)$ python setup.py develop --user
    running develop
    running egg_info
    writing requirements to apricot.egg-info/requires.txt
    writing apricot.egg-info/PKG-INFO
    writing top-level names to apricot.egg-info/top_level.txt
    writing dependency_links to apricot.egg-info/dependency_links.txt
    reading manifest file 'apricot.egg-info/SOURCES.txt'
    writing manifest file 'apricot.egg-info/SOURCES.txt'
    running build_ext
    Creating /home/apahim/.local/lib/python2.7/site-packages/apricot.egg-link (link to .)
    apricot 1.0 is already the active version in easy-install.pth

    Installed /home/apahim/git/apricot
    Processing dependencies for apricot==1.0
    Searching for avocado-framework==55.0
    Best match: avocado-framework 55.0
    avocado-framework 55.0 is already the active version in easy-install.pth

    Using /home/apahim/git/avocado
    Using /usr/lib/python2.7/site-packages
    Searching for six==1.10.0
    Best match: six 1.10.0
    Adding six 1.10.0 to easy-install.pth file

    Using /usr/lib/python2.7/site-packages
    Searching for pbr==3.1.1
    Best match: pbr 3.1.1
    Adding pbr 3.1.1 to easy-install.pth file
    Installing pbr script to /home/apahim/.local/bin

    Using /usr/lib/python2.7/site-packages
    Finished processing dependencies for apricot==1.0

And to run your test::

    ~/git/apricot$ avocado run tests/test_example.py
    JOB ID     : 02c663eb77e0ae6ce67462a398da6972791793bf
    JOB LOG    : $HOME/avocado/job-results/job-2017-11-16T12.44-02c663e/job.log
     (1/1) tests/test_example.py:MyTest.test: PASS (0.03 s)
    RESULTS    : PASS 1 | ERROR 0 | FAIL 0 | SKIP 0 | WARN 0 | INTERRUPT 0 | CANCEL 0
    JOB TIME   : 0.95 s
    JOB HTML   : $HOME/avocado/job-results/job-2017-11-16T12.44-02c663e/results.html
