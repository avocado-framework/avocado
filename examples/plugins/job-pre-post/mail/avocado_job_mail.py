import logging
import smtplib
from email.mime.text import MIMEText

from avocado.core.settings import settings
from avocado.plugins.base import JobPrePost


class Mail(JobPrePost):

    name = 'mail'
    description = 'Sends mail to notify on job start/end'

    def run(self, job):
        log = logging.getLogger("avocado.app")
        rcpt = settings.get_value(section="plugins.job.mail",
                                  key="recipient",
                                  key_type=str,
                                  default='root@localhost.localdomain')
        subject = settings.get_value(section="plugins.job.mail",
                                     key="subject",
                                     key_type=str,
                                     default='[AVOCADO JOB NOTIFICATION]')
        sender = settings.get_value(section="plugins.job.mail",
                                    key="sender",
                                    key_type=str,
                                    default='avocado@localhost.localdomain')
        server = settings.get_value(section="plugins.job.mail",
                                    key="server",
                                    key_type=str,
                                    default='localhost')

        # build proper subject based on job status
        subject += '- Job %s - Status: %s' % (job.unique_id,
                                              job.status)
        msg = MIMEText(subject)
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = rcpt

        # So many possible failures, let's just tell the user about it
        try:
            smtp = smtplib.SMTP(server)
            smtp.sendmail(sender, [rcpt], msg.as_string())
            smtp.quit()
        except:
            log.error("Failure to send email notification: "
                      "please check your mail configuration")
