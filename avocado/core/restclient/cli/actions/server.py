# Copyright: Red Hat Inc. 2015
# Author: Cleber Rosa <cleber@redhat.com>

"""
Module that implements the actions for the CLI App when the job toplevel
command is used
"""

from . import base
from ... import connection
from ....output import LOG_UI


@base.action
def status(app):
    """
    Shows the server status
    """
    data = app.connection.request("version/")
    LOG_UI.info("Server version: %s", data.get('version'))


@base.action
def list_brief(app):
    """
    Shows the server API list
    """
    try:
        data = app.connection.get_api_list()
    except connection.UnexpectedHttpStatusCode as e:
        if e.received == 403:
            LOG_UI.error("Error: Access Forbidden")
            return False

    LOG_UI.info("Available APIs:")
    for name in data:
        LOG_UI.info(" * %s", name)
