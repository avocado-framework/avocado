import smtplib
from email.mime.text import MIMEText

from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import Init, JobPost, JobPre
from avocado.core.settings import settings


class MailInit(Init):
    name = 'mail-init'
    description = 'Mail plugin initialization'

    def initialize(self):
        help_msg = 'Mail recipient.'
        settings.register_option(section='plugins.job.mail',
                                 key='recipient',
                                 default='root@localhost.localdomain',
                                 help_msg=help_msg)

        help_msg = 'Mail header.'
        settings.register_option(section='plugins.job.mail',
                                 key='header',
                                 default='[AVOCADO JOB NOTIFICATION]',
                                 help_msg=help_msg)

        help_msg = 'Mail sender.'
        settings.register_option(section='plugins.job.mail',
                                 key='sender',
                                 default='avocado@localhost.localdomain',
                                 help_msg=help_msg)

        help_msg = 'Mail server.'
        settings.register_option(section='plugins.job.mail',
                                 key='server',
                                 default='localhost',
                                 help_msg=help_msg)


class Mail(JobPre, JobPost):
    name = 'mail'
    description = 'Sends mail to notify on job start/end'

    @staticmethod
    def mail(job):
        rcpt = job.config.get('plugins.job.mail.recipient')
        header = job.config.get('plugins.job.mail.header')
        sender = job.config.get('plugins.job.mail.sender')
        server = job.config.get('plugins.job.mail.server')
        # build proper subject based on job status
        subject = f'{header} Job {job.unique_id} - Status: {job.status}'
        msg = MIMEText(subject)
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = rcpt

        # So many possible failures, let's just tell the user about it
        try:
            smtp = smtplib.SMTP(server)
            smtp.sendmail(sender, [rcpt], msg.as_string())
            smtp.quit()
        except Exception:  # pylint: disable=W0703
            LOG_UI.error("Failure to send email notification: "
                         "please check your mail configuration")

    pre = post = mail
