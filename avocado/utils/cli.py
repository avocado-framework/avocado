import logging

log = logging.getLogger('avocado.test')


def ask(question, auto=False):
    """
    Raw input with a prompt.

    :param question: Question to be asked
    :param auto: Whether to return "y" instead of asking the question
    """
    if auto:
        log.info("%s (y/n) y" % question)
        return "y"
    return raw_input("%s (y/n) " % question)
