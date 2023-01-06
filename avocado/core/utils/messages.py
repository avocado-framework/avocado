import time


class GenericFactory:
    message_status = None

    @classmethod
    def _prepare_message(cls, additional_info=None):
        """Prepare a message dict with some basic information.

        This will add the keyword 'status' and 'time' to all messages.

        :param: addional_info: Any additional information that you
                               would like to add to the message.
        :type additional_info: dict
        :return: message dict which can be send to avocado server
        :rtype: dict
        """
        status = {}
        if additional_info is not None:
            status = additional_info
        status.update({"status": cls.message_status, "time": time.monotonic()})
        return status

    @classmethod
    def get(cls, **kwargs):
        """Creates message base on it's type with all necessary information.

        :return: message dict which can be send to avocado server
        :rtype: dict
        """
        kwargs = {key: value for (key, value) in kwargs.items() if value is not None}
        return cls._prepare_message(additional_info=kwargs)


class StartedFactory(GenericFactory):
    message_status = "started"


class RunningFactory(GenericFactory):
    """Creates running message without any additional info."""

    message_status = "running"


class FinishedFactory(GenericFactory):
    message_status = "finished"

    @classmethod
    def get(cls, result, fail_reason=None, returncode=None):  # pylint: disable=W0221
        """Creates finished message with all necessary information.

        :param result: test result
        :type result values for the statuses defined in
                     :class: avocado.core.teststatus.STATUSES
        :param fail_reason: parameter for brief specification, of the failed
                            result.
        :type fail_reason: str
        :param returncode: exit status of runner
        :return: finished message
        :rtype: dict
        """
        return super().get(
            result=result, fail_reason=fail_reason, returncode=returncode
        )


class GenericRunningFactory(GenericFactory):
    message_status = "running"
    message_type = None

    @classmethod
    def _get_running_message(cls, msg):
        """Prepare a message dict with necessary information for specific type.

        :param msg: message data. If the message is str, it will be encoded
                    with utf-8.
        :type msg: str, bytes
        :return: message dict which can be send to avocado server
        :rtype: dict
        """
        message = {"type": cls.message_type, "log": msg}
        if type(msg) is not bytes:
            msg = msg.encode("utf-8")
            message.update({"log": msg, "encoding": "utf-8"})
        return message

    @classmethod
    def get(cls, msg, **kwargs):  # pylint: disable=W0221
        """Creates running message with all necessary information.

        :param msg: log of running message
        :type msg: str
        :return: running message
        :rtype: dict
        """
        kwargs.update(cls._get_running_message(msg))
        return super().get(**kwargs)


class LogFactory(GenericRunningFactory):
    message_type = "log"


class StdoutFactory(GenericRunningFactory):
    """Creates stdout message with all necessary information."""

    message_type = "stdout"


class StderrFactory(GenericRunningFactory):
    """Creates stderr message with all necessary information."""

    message_type = "stderr"


class WhiteboardFactory(GenericRunningFactory):
    """Creates whiteboard message with all necessary information."""

    message_type = "whiteboard"


class OutputFactory(GenericRunningFactory):
    """Creates output message with all necessary information."""

    message_type = "output"


class FileFactory(GenericRunningFactory):
    """Creates file message with all necessary information."""

    message_type = "file"

    @classmethod
    def get(cls, msg, path):  # pylint: disable=W0221
        return super().get(msg=msg, path=path)
