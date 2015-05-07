# Copyright: Red Hat Inc. 2015
# Author: Cleber Rosa <cleber@redhat.com>

"""
Module that implements the actions for the CLI App when the job toplevel
command is used
"""

from avocado.core.restclient import connection
from avocado.core.restclient.cli.actions import base


@base.action
def status(app):
    """
    Shows the server status
    """
    data = app.connection.request("version/")
    app.view.notify(event="message",
                    msg="Server version: %s" % data.get('version'))


@base.action
def list_brief(app):
    """
    Shows the server API list
    """
    try:
        data = app.connection.get_api_list()
    except connection.UnexpectedHttpStatusCode, e:
        if e.received == 403:
            app.view.notify(event="error",
                            msg="Error: Access Forbidden")
            return False

    app.view.notify(event="message",
                    msg="Available APIs:")
    for name in data:
        app.view.notify(event="message",
                        msg=" * %s" % name)
