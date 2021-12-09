"""
beaker result plugin

Sends results and logs to beaker using the harness API.
https://beaker-project.org/docs/alternative-harnesses/index.html

Finds the beaker API entry point using the BEAKER_LAB_CONTROLLER_URL
environment variable.  Does nothing in case the variable is not set.

"""
import glob
import os
import pprint
import urllib.error
import urllib.parse
import urllib.request

from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import ResultEvents


class BeakerResult(ResultEvents):

    """
    send test results to beaker test harness api
    """

    name = 'beaker'
    description = 'report results to beaker'

    beaker_url = None
    job_id = None

    def __init__(self, config=None):  # pylint: disable=W0613
        baseurl = os.environ.get('BEAKER_LAB_CONTROLLER_URL')
        recipeid = os.environ.get('RSTRNT_RECIPEID')
        taskid = os.environ.get('RSTRNT_TASKID')
        if not all([baseurl, recipeid, taskid]):
            return
        baseurl = baseurl.rstrip('/')
        self.beaker_url = baseurl + '/recipes/' + recipeid + '/tasks/' + taskid
        LOG_UI.info("beaker: using API at %s (R:%s T:%s)", baseurl, recipeid, taskid)

    def send_request(self, req):
        LOG_UI.debug('beaker: %s %s ...', req.method, req.full_url)
        try:
            res = urllib.request.urlopen(req)  # nosec
            return res
        except urllib.error.URLError as err:
            LOG_UI.info('beaker: %s %s failed: %s', req.method, req.full_url, err)
            return None
        except Exception as err:
            # should not happen
            LOG_UI.info('beaker: Oops: %s', err)
            return None

    def post_result(self, state):
        reqdict = {
            'path': "%s/%s" % (self.job_id, state.get('name')),
        }

        result = state.get('status').lower().capitalize()
        if result == 'Cancel':
            result = 'Skip'
        if result not in ['Pass', 'Fail', 'Skip']:
            result = 'Fail'
        reqdict['result'] = result

        reason = state.get('fail_reason')
        if reason is not None:
            reqdict['message'] = reason

        secs = state.get('time_elapsed')
        if secs is not None:
            reqdict['score'] = str(int(secs))

        reqdata = urllib.parse.urlencode(reqdict).encode('utf-8')
        url = self.beaker_url + '/results/'
        req = urllib.request.Request(url, method='POST', data=reqdata)
        res = self.send_request(req)
        if res is None:
            return None
        return res.getheader('Location')

    def put_data(self, location, name, content):
        url = location + '/logs/' + name
        req = urllib.request.Request(url, method='PUT', data=content)
        self.send_request(req)

    def put_file(self, location, name, filename):
        file = open(filename)
        content = file.read().encode('utf-8')
        file.close()
        self.put_data(location, name, content)

    def put_file_list(self, location, prefix, filelist):
        for file in filelist:
            if os.path.isfile(file) and os.path.getsize(file) > 0:
                name = prefix + os.path.basename(file)
                self.put_file(location, name, file)

    def pre_tests(self, job):
        self.job_id = job.unique_id[:6]
        return

    def start_test(self, result, state):
        return

    def test_progress(self, progress=False):
        return

    def end_test(self, result, state):
        if self.beaker_url is None:
            return

        location = self.post_result(state)
        if location is None:
            return

        logfile = state.get('logfile')
        self.put_file(location, 'logfile', logfile)

        ppstate = pprint.pformat(state).encode('utf8')
        self.put_data(location, 'state', ppstate)

        pattern = os.path.join(state.get('logdir'), '*')
        filelist = [f for f in glob.glob(pattern) if f != logfile]
        self.put_file_list(location, '', filelist)

    def post_tests(self, job):
        if self.beaker_url is None:
            return

        pattern = os.path.join(job.logdir, '*')
        filelist = glob.glob(pattern)
        self.put_file_list(self.beaker_url, self.job_id + '-', filelist)
