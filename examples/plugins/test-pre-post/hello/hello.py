from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import PostTest, PreTest


class HelloWorld(PreTest, PostTest):

    name = "hello"
    description = "The classical Hello World! plugin example."
    is_cacheable = True

    def pre_test_runnables(self, test_runnable, suite_config=None):
        LOG_UI.info(self.description)

    def post_test_runnables(self, test_runnable, suite_config=None):
        LOG_UI.info(self.description)
