from setuptools import setup

name = "rogue"
module = "avocado_rogue"
resolver_ep = f"{name} = {module}.resolver:RogueResolver"
runner_ep = f"{name} = {module}.runner:RogueRunner"
runner_script = f"avocado-runner-{name} = {module}.runner:main"


if __name__ == "__main__":
    setup(
        name="avocado-rogue",
        version="1.0",
        description='Avocado "rogue" test type',
        long_description=(
            "This is a plugin that contains a rogue runner, that is, "
            "a runner that will try to never allow to be terminated."
        ),
        py_modules=[module],
        entry_points={
            "avocado.plugins.resolver": [resolver_ep],
            "avocado.plugins.runnable.runner": [runner_ep],
            "console_scripts": [runner_script],
        },
    )
