# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

import os
import urllib2
import logging

from avocado.plugins import plugin
from avocado.core import output
from avocado.core import data_dir
from avocado.utils import download
from avocado.utils import path
from avocado.utils import crypto


class VirtBootstrap(plugin.Plugin):

    """
    Implements the avocado 'virt-bootstrap' subcommand
    """

    name = 'virt_bootstrap'
    enabled = True
    app_logger = logging.getLogger('avocado.app')

    def configure(self, parser):
        self.parser = parser.subcommands.add_parser(
            'virt-bootstrap',
            help='Download image files important to avocado virt tests')
        super(VirtBootstrap, self).configure(self.parser)

    def run(self, args):
        bcolors = output.term_support
        jeos_sha1_url = 'https://lmr.fedorapeople.org/jeos/SHA1SUM_JEOS20'
        self.app_logger.info(bcolors.header_str("Checking if JeOS is in the right location and matching SHA1"))
        try:
            self.app_logger.info("Verifying expected SHA1 sum from %s" % jeos_sha1_url)
            sha1_file = urllib2.urlopen(jeos_sha1_url)
            sha1_contents = sha1_file.read()
            sha1 = sha1_contents.split(" ")[0]
            self.app_logger.info("Expected SHA1 sum: %s" % sha1)
        except Exception, e:
            self.app_logger.error("Failed to get SHA1 from file: %s" % e)

        jeos_dst_dir = path.init_dir(os.path.join(data_dir.get_data_dir(),
                                                  'images'))
        jeos_dst_path = os.path.join(jeos_dst_dir, 'jeos-20-64.qcow2.7z')

        if os.path.isfile(jeos_dst_path):
            actual_sha1 = crypto.hash_file(filename=jeos_dst_path,
                                           algorithm="sha1")
        else:
            actual_sha1 = '0'

        if actual_sha1 != sha1:
            if actual_sha1 == '0':
                self.app_logger.info("JeOS could not be found at %s. "
                                     "Downloading it (173 MB). Please wait..." %
                                     jeos_dst_path)
            else:
                self.app_logger.info("JeOS at %s is either corrupted or outdated. "
                                     "Downloading a new copy (173 MB). Please wait..." %
                                     jeos_dst_path)
            jeos_url = 'https://lmr.fedorapeople.org/jeos/jeos-20-64.qcow2.7z'
            try:
                download.url_download(jeos_url, jeos_dst_path)
            except:
                self.app_logger.info(bcolors.fail_header_str("Exiting upon user "
                                                             "request (Download "
                                                             "not finished)"))
        else:
            self.app_logger.info("JeOS in the right location, with matching SHA1. "
                                 "Nothing to do")
