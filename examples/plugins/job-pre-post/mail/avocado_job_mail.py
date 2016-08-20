import os
import sys
import json
import logging
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from avocado.core.settings import settings
from avocado.core.plugin_interfaces import JobPre, JobPost, CLI


class MailCLI(CLI):

    """
    Mail report plugin
    """

    name = 'mail'
    description = "Mail config options for 'run' command"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        msg = 'mail report config options'
        self.remote_parser = run_subcommand_parser.add_argument_group(msg)
        self.remote_parser.add_argument('--mail-enable', dest='mail_job',
                                        choices=('on', 'off', 'default'), default='default',
                                        help=('Enables email result report'))

        self.remote_parser.add_argument('--mail-to',
                                        dest='mail_job_to', default=None,
                                        help='Set To: address, overwrite default recepinet')

        self.remote_parser.add_argument('--mail-cc', nargs='*', default=[],
                                        dest='mail_job_cc',
                                        help='List of recipients add to Cc:')

        self.remote_parser.add_argument('--mail-subject', type=str, dest='mail_job_subject',
                                        default=None,
                                        help='Append string to subject')

        self.remote_parser.add_argument('--mail-type', type=str, dest='mail_job_type',
                                        choices=('minimal', 'info', 'full'),
                                        default='full',
                                        help=('Select email report type: \n'
                                              'minimal: only job id, '
                                              'info: add information for all tests, '
                                              'full: info and attach results archive'))

    def run(self, args):
        pass


class Mail(JobPre, JobPost):

    name = 'mail'
    description = 'Sends mail to notify on job start/end'

    def __init__(self):
        self.enabled = 0
        self.log = logging.getLogger("avocado.app")

    def parse_job_opts(self, job):
        configured = settings.get_value(section="plugins.job.mail",
                                        key="configured",
                                        key_type=str,
                                        default='no')
        if configured == 'yes':
            self.enabled = 1

        self.rcpt = settings.get_value(section="plugins.job.mail",
                                       key="recipient",
                                       key_type=str,
                                       default='root@localhost.localdomain')
        self.subject = settings.get_value(section="plugins.job.mail",
                                          key="subject",
                                          key_type=str,
                                          default='[AVOCADO JOB NOTIFICATION]')
        self.sender = settings.get_value(section="plugins.job.mail",
                                         key="sender",
                                         key_type=str,
                                         default='avocado@localhost.localdomain')
        self.server = settings.get_value(section="plugins.job.mail",
                                         key="server",
                                         key_type=str,
                                         default='localhost')

        if (hasattr(job.args, 'mail_job')):
            state = getattr(job.args, 'mail_job')
            if state == 'on':
                self.enabled = 1
            if state == 'off':
                self.enabled = 0

        if hasattr(job.args, 'mail_job_to'):
            if getattr(job.args, 'mail_job_to') is not None:
                self.rcpt = getattr(job.args, 'mail_job_to')

        self.rcpt_cc = []
        if hasattr(job.args, 'mail_job_cc'):
            if getattr(job.args, 'mail_job_cc') is not None:
                self.rcpt_cc = getattr(job.args, 'mail_job_cc')

        if hasattr(job.args, 'mail_job_subject'):
            if getattr(job.args, 'mail_job_subject') is not None:
                self.subject = self.subject + getattr(job.args, 'mail_job_subject')

        if hasattr(job.args, 'mail_job_type'):
            if getattr(job.args, 'mail_job_type') is not None:
                self.body_type = getattr(job.args, 'mail_job_type')

    def pre(self, job):
        return

    def _make_stats(self):

        j = self.results

        stat = ''
        if j['total'] == j['pass']:
            stat = 'ALLPASS (%d/%d)' % (j['total'], j['pass'])
        else:
            stat = 'TOTAL %d, PASS %d' % (j['total'], j['pass'])
            if j['errors'] > 0:
                stat = stat + ", ERROR %d" % j['errors']
            if j['failures'] > 0:
                stat = stat + ", FAIL %d" % j['failures']

            if j['skip'] > 0:
                stat = stat + ", SKIP %d" % j['skip']

        return stat

    def _make_body(self):
        idx = 1
        j = self.results

        out = StringIO()
        out.write('CMDLINE    : ' + " ".join(sys.argv) + '\n')
        out.write("TESTS      : %d\n" % j['total'])
        for t in j['tests']:
            out.write(" (%d/%d) [%s] %s (%.2f s)\n" %
                      (idx, j['total'], t['status'], t['test'].ljust(40),
                       t['end'] - t['start']))
            if (not t['fail_reason'] == 'None'):
                out.write("          %s\n" % t['fail_reason'])
            idx = idx + 1

        out.write("RESULTS    : PASS %d | ERROR %d | FAIL %d | SKIP %d\n" %
                  (j['pass'], j['errors'], j['failures'], j['skip']))
        out.write('TESTS TIME : %.2f s\n' % j['time'])

        return MIMEText(out.getvalue())

    def _try_attach(self, mime, path, mime_type='octet-stream'):
        if os.path.exists(path):
            self.log.debug('try attach %s' % path)
            fp = open(path, 'rb')
            if not mime_type == 'text':
                part = MIMEBase('application', mime_type)
                part.set_payload(fp.read())
                if mime_type == 'octet-stream':
                    encoders.encode_base64(part)
                desc = 'attachment; filename="%s"' % os.path.basename(path)
                part.add_header('Content-Disposition', desc)
            else:
                part = MIMEText(fp.read())
            fp.close()
            mime.attach(part)
        else:
            self.log.debug('try_attach %s not exits' % path)

    def mail_report(self, job):

        self.parse_job_opts(job)
        if not self.enabled:
            return

        msg = MIMEMultipart('text')
        msg['From'] = self.sender
        msg['To'] = self.rcpt
        msg['Cc'] = ', '.join(self.rcpt_cc)

        if self.body_type == 'minimal':
            # build proper subject based on job status
            self.subject = '%s Job %s - Status: %s' % (self.subject,
                                                       job.unique_id,
                                                       job.status)
        else:
            #part1 = MIMEMessage('text', 'plain')
            #part1 = MIMEMessage('text')
            json_path = os.path.join(job.logdir, 'results.json')

            try:
                fp = open(json_path, 'rb')
                self.results = json.loads(fp.read())
                self.subject = '%s Job %s - %s : ' % (self.subject,
                                                      job.unique_id[:7],
                                                      job.status)
                fp.close()
                msg['Subject'] = self.subject + self._make_stats()
                body = self._make_body()
                msg.attach(body)
                # Jobscripts plugin or tests may generate extra data for us
                email_report = os.path.join(job.logdir, 'email_report')
                self._try_attach(msg, os.path.join(job.logdir, 'email_report'), 'text')
                self._try_attach(msg, json_path, 'json')
            except Exception as e:
                self.log.error('Can not parse results.json')
                self.log.error(e)
                return

        if self.body_type == 'full':
            self._try_attach(msg, os.path.join(job.logdir, 'results.html'))
            self._try_attach(msg, job.logdir + '.zip')
            #self._try_attach(msg, job.logdir + '.tar.xz')

        self.log.debug('Email generated:%s' % msg.as_string())
        ###
        # So many possible failures, let's just tell the user about it
        try:
            smtp = smtplib.SMTP(self.server)
            smtp.sendmail(self.sender, [self.rcpt] + self.rcpt_cc, msg.as_string())
            smtp.quit()
        except:
            self.log.error("Failure to send email notification: "
                           "please check your mail configuration")

    post = mail_report
