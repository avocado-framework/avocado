'''
This module implements classes that allow a user to create, enable and disable
YUM repositories on the system.
'''


import os


__all__ = ['REPO_DIR', 'YumRepo']


REPO_DIR = '/etc/yum.repos.d'


class YumRepo(object):

    '''
    Represents a YUM repository

    The goal of this class is not to give access to all features of a YUM
    Repository, but to provide a simple way to configure a valid one during
    a test run.

    Sample usage:
       >>> mainrepo = YumRepo("main", "http://download.project.org/repo",
                              "/etc/yum.repos.d/main.repo")

    Or to use a default path:
       >>> mainrepo = YumRepo("main", 'http://download.project.org/repo')

    And then:
       >>> mainrepo.save()

    When it comes to the repo URL, currently there's no support for setting a
    mirrorlist, only a baseurl.
    '''

    def __init__(self, name, baseurl, path=None):
        '''
        Initilizes a new YumRepo object

        If path is not given, it is assumed to be "$(name)s.repo" at
        the default YUM repo directory.

        :param name: the repository name
        :param path: the full path of the file that defines this repository
        '''
        self.name = name
        self.path = path
        if self.path is None:
            self.path = self._get_path_from_name(self.name)

        self.baseurl = baseurl

        self.enabled = True
        self.gpgcheck = False
        self.gpgkey = ''

    @classmethod
    def _get_path_from_name(cls, name):
        '''
        Returns the default path for the a repo of a given name

        :param name: the repository name
        :return: the default repo file path for the given name
        '''
        return os.path.join(REPO_DIR, "%s.repo" % name)

    @classmethod
    def _yum_value_for_boolean(cls, boolean):
        '''
        Returns a boolean in YUM acceptable syntax
        '''
        if boolean:
            return '1'
        else:
            return '0'

    def render(self):
        '''
        Renders the repo file

        Yes, we could use ConfigParser for this, but it produces files with
        spaces between keys and values, which look akward by YUM defaults.
        '''
        template = ("[%(name)s]\n"
                    "name=%(name)s\n"
                    "baseurl=%(baseurl)s\n"
                    "enabled=%(enabled)s\n"
                    "gpgcheck=%(gpgcheck)s\n"
                    "gpgkey=%(gpgkey)s\n")

        values = {'name': self.name,
                  'baseurl': self.baseurl,
                  'enabled': self._yum_value_for_boolean(self.enabled),
                  'gpgcheck': self._yum_value_for_boolean(self.gpgcheck),
                  'gpgkey': self.gpgkey}

        return template % values

    def save(self):
        '''
        Saves the repo file
        '''
        output_file = open(self.path, 'w')
        output_file.write(self.render())
        output_file.close()

    def remove(self):
        '''
        Removes the repo file
        '''
        if os.path.exists(self.path):
            os.unlink(self.path)
