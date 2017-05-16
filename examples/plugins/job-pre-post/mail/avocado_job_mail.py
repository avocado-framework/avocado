import smtplib
from email.mime.text import MIMEText

from avocado.core.output import LOG_UI
from avocado.core.settings import settings
from avocado.core.plugin_interfaces import JobPre, JobPost


class Mail(JobPre, JobPost):

    name = 'mail'
    description = 'Sends mail to notify on job start/end'

    def __init__(self):
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

    def mail(self, job):
        # build proper subject based on job status
        subject = '%s Job %s - Status: %s' % (self.subject,
                                              job.unique_id,
                                              job.status)
        msg = MIMEText(subject)
        msg['Subject'] = self.subject
        msg['From'] = self.sender
        msg['To'] = self.rcpt

        # So many possible failures, let's just tell the user about it
        try:
            smtp = smtplib.SMTP(self.server)
            smtp.sendmail(self.sender, [self.rcpt], msg.as_string())
            smtp.quit()
        except:
            LOG_UI.error("Failure to send email notification: "
                         "please check your mail configuration")

    pre = post = mail
