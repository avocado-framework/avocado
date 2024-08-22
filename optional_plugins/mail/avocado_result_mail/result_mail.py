import json
import logging
import os
import smtplib
import time
from email.mime.text import MIMEText

from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import Init, JobPost, JobPre
from avocado.core.settings import settings

# Create a logger for avocado.job.mail
job_log = logging.getLogger("avocado.job.mail")


class MailInit(Init):
    name = "mail-init"
    description = "Mail plugin initialization"

    def initialize(self):
        help_msg = "Mail recipient."
        settings.register_option(
            section="plugins.mail",
            key="recipient",
            default=None,
            help_msg=help_msg,
        )

        help_msg = "Mail header."
        settings.register_option(
            section="plugins.mail",
            key="header",
            default="[AVOCADO JOB NOTIFICATION]",
            help_msg=help_msg,
        )

        help_msg = "Mail sender."
        settings.register_option(
            section="plugins.mail",
            key="sender",
            default=None,
            help_msg=help_msg,
        )

        help_msg = "Mail server."
        settings.register_option(
            section="plugins.mail",
            key="server",
            default=None,
            help_msg=help_msg,
        )

        help_msg = "Mail server port."
        settings.register_option(
            section="plugins.mail",
            key="port",
            default=None,
            help_msg=help_msg,
        )

        help_msg = "Mail server Application Password."
        settings.register_option(
            section="plugins.mail",
            key="password",
            default=None,
            help_msg=help_msg,
        )

        help_msg = "Email detail level."
        settings.register_option(
            section="plugins.mail",
            key="verbose",
            default=False,
            help_msg=help_msg,
            key_type=bool,
        )


class Mail(JobPre, JobPost):
    name = "mail"
    description = "Sends mail to notify on job start/end"

    def __init__(self):
        super().__init__()
        self.enabled = True
        self.start_email_sent = False

    def initialize(self, job):
        if not self._validate_email_config(job):
            self.enabled = False
        super().initialize(job)

    @staticmethod
    def _get_smtp_config(job):
        return (
            job.config.get("plugins.mail.server"),
            job.config.get("plugins.mail.port"),
            job.config.get("plugins.mail.sender"),
            job.config.get("plugins.mail.password", ""),
        )

    @staticmethod
    def _build_message(job, time_content, phase, finishedtime="", test_summary=""):
        if phase == "Post":
            subject_prefix = "Job Completed"
        else:
            subject_prefix = "Job Started"

        body = f"""
        <html>
            <body>
                <h2>Job Notification - Job {job.unique_id}</h2>
        """

        if phase == "Post":
            body += f"""
                <p><strong>Job Total Time:</strong> {time_content}</p>
            """

            body += f"""
                <p><strong>Job Finished At:</strong> {finishedtime}</p>
                <p><strong>Results:</strong></p>
                <ul>
                    <li>PASS: {job.result.passed}</li>
                    <li>ERROR: {job.result.errors}</li>
                    <li>FAIL: {job.result.failed}</li>
                    <li>SKIP: {job.result.skipped}</li>
                    <li>WARN: {job.result.warned}</li>
                    <li>INTERRUPT: {job.result.interrupted}</li>
                    <li>CANCEL: {job.result.cancelled}</li>
                </ul>
                <p><strong>Test Summary:</strong></p>
                <pre>{test_summary}</pre>
            """
        elif phase == "Start":
            body += f"""
                <p><strong>Job Started At:</strong> {time_content}</p>
            """

        body += """
            </body>
        </html>
        """

        msg = MIMEText(body, "html")
        msg["Subject"] = (
            f"{job.config.get('plugins.mail.header')} Job {job.unique_id} - Status: {subject_prefix}"
        )
        msg["From"] = job.config.get("plugins.mail.sender")
        msg["To"] = job.config.get("plugins.mail.recipient")
        return msg

    @staticmethod
    def _send_email(smtp, sender, rcpt, msg):
        try:
            smtp.sendmail(sender, [rcpt], msg.as_string())
            LOG_UI.info("EMAIL SENT TO: %s", rcpt)
        except Exception as e:
            job_log.error(f"Failure to send email notification to {rcpt}: {e}")

    @staticmethod
    def _smtp_login_and_send(job, msg):
        if not Mail._validate_email_config(job):
            job_log.error("Invalid email configuration. Plugin Disabled.")
            return False

        server, port, sender, password = Mail._get_smtp_config(job)
        smtp = Mail._create_smtp_connection(server, port)
        if smtp:
            try:
                smtp.login(sender, password)
            except Exception as e:
                job_log.error(f"SMTP login failed: {e}")
                return False

            Mail._send_email(
                smtp, sender, job.config.get("plugins.mail.recipient"), msg
            )
            smtp.quit()
            return True
        else:
            job_log.error(
                "Failed to establish SMTP connection. Skipping email notification."
            )
            return False

    @staticmethod
    def _create_smtp_connection(server, port):
        try:
            smtp = smtplib.SMTP(server, port)
            smtp.starttls()  # Enable TLS
            return smtp
        except Exception as e:  # pylint: disable=W0703
            job_log.error(
                f"Failed to establish SMTP connection to {server}:{port}: {e}"
            )
            return None

    @staticmethod
    def _read_results_file(results_path):
        try:
            with open(results_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            job_log.error("Test summary file not found at %s.", results_path)
            return None
        except json.JSONDecodeError:
            job_log.error("Error decoding JSON from file %s.", results_path)
            return None
        except Exception as e:
            job_log.error("Unexpected error while reading test summary: %s", str(e))
            return None

    @staticmethod
    def _format_test_details(test, advanced=False):
        if advanced:
            details = [
                f"<strong>Name:</strong> {test.get('name', '')}<br>",
                f"<strong>Status:</strong> {test.get('status', '')}<br>",
                f"<strong>Fail Reason:</strong> {test.get('fail_reason', '')}<br>",
                f"<strong>Actual Time Start:</strong> {test.get('actual_time_start', '')}<br>",
                f"<strong>Actual Time End:</strong> {test.get('actual_time_end', '')}<br>",
                f"<strong>ID:</strong> {test.get('id', '')}<br>",
                f"<strong>Log Directory:</strong> {test.get('logdir', '')}<br>",
                f"<strong>Log File:</strong> {test.get('logfile', '')}<br>",
                f"<strong>Time Elapsed:</strong> {test.get('time_elapsed', '')}<br>",
                f"<strong>Time Start:</strong> {test.get('time_start', '')}<br>",
                f"<strong>Time End:</strong> {test.get('time_end', '')}<br>",
                f"<strong>Tags:</strong> {test.get('tags', '')}<br>",
                f"<strong>Whiteboard:</strong> {test.get('whiteboard', '')}<br>",
            ]
        else:
            details = [
                f"<strong>Name:</strong> {test.get('name', '')}<br>",
                f"<strong>Fail Reason:</strong> {test.get('fail_reason', '')}<br>",
            ]
        return "".join(details)

    @staticmethod
    def _generate_test_summary(data, verbose):
        test_summary = []

        def format_test_details(test):
            return Mail._format_test_details(test, advanced=verbose)

        for test in data.get("tests", []):
            if test.get("status") == "FAIL":
                test_summary.append(format_test_details(test))

        return "\n\n".join(test_summary)

    @staticmethod
    def _get_test_summary(job):
        results_path = os.path.join(job.logdir, "results.json")
        data = Mail._read_results_file(results_path)
        if not data:
            return ""

        verbose = job.config.get("plugins.mail.verbose")
        return Mail._generate_test_summary(data, verbose)

    def pre(self, job):
        if not self.enabled:
            job_log.info("Email plugin disabled, skipping start notification.")
            return

        phase = "Start"
        start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        time_content = f"{start_time}"

        msg = self._build_message(job, time_content, phase)
        self.start_email_sent = self._smtp_login_and_send(job, msg)

    def post(self, job):
        if not self.enabled or not self.start_email_sent:
            job_log.info(
                "Email plugin disabled or start email not sent, skipping end notification."
            )
            return

        phase = "Post"
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        finishedtime = f"{current_time}"

        time_elapsed_formatted = f"{job.time_elapsed:.2f}"
        time_content = f"{time_elapsed_formatted} Seconds"

        test_summary = self._get_test_summary(job)

        msg = self._build_message(job, time_content, phase, finishedtime, test_summary)
        self._smtp_login_and_send(job, msg)

    @staticmethod
    def _validate_email_config(job):
        server, port, sender, password = Mail._get_smtp_config(job)

        if not all([server, port, sender, password]):
            job_log.error(
                "Email configuration is missing or contains empty values. Disabling Plugin."
            )
            return False
        return True
