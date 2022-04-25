import json
import re
import sys

import jsonschema

from avocado import Test, fail_on
from avocado.utils import process


class Interface(Test):

    def get_runner(self):
        default_runner = f"{sys.executable} -m avocado.core.nrunner"
        return self.params.get("runner", default=default_runner)

    @staticmethod
    def guess_recipe_from_runner(runner, recipe_type):
        recipe_file_name = f"recipe_{recipe_type}"
        match = re.match(r'^avocado-runner-(.*)$', runner)
        if match:
            underlined = match.group(1).replace('-', '_')
            recipe_file_name += f"_{underlined}.json"
        else:
            recipe_file_name += ".json"
        return recipe_file_name

    @fail_on(process.CmdError)
    def test_help(self):
        """
        Makes sure a runner can be called with --help and that the
        basic required commands are present in the help message
        """
        cmd = f"{self.get_runner()} --help"
        result = process.run(cmd)
        self.assertIn(b"capabilities", result.stdout,
                      "Mention to capabilities command not found")

    @fail_on(process.CmdError)
    @fail_on(jsonschema.exceptions.ValidationError)
    def test_schema_capabilities(self):
        cmd = f"{self.get_runner()} capabilities"
        result = process.run(cmd)
        capabilities = json.loads(result.stdout_text)
        schema_path = self.get_data("capabilities.schema.json")
        if not schema_path:
            self.error('Schema file not found for "capabilities"')
        with open(schema_path, 'r', encoding='utf-8') as schema:
            jsonschema.validate(capabilities, json.load(schema))

    def test_runnable_run_no_args(self):
        cmd = f"{self.get_runner()} runnable-run"
        result = process.run(cmd, ignore_status=True)
        expected = int(self.params.get('runnable-run-no-args-exit-code',
                                       default=2))
        self.assertEqual(result.exit_status, expected)

    def test_runnable_run_uri_only(self):
        cmd = f"{self.get_runner()} runnable-run -u some_uri"
        result = process.run(cmd, ignore_status=True)
        expected = int(self.params.get('runnable-run-uri-only-exit-code',
                                       default=2))
        self.assertEqual(result.exit_status, expected)

    def test_runnable_run_recipe_no_args(self):
        """
        Makes sure the recipe argument is required
        """
        cmd = f"{self.get_runner()} runnable-run-recipe"
        result = process.run(cmd, ignore_status=True)
        self.assertEqual(result.exit_status, 2)

    def test_runnable_run_recipe_specific_kind(self):
        runner = self.get_runner()
        recipe_file = self.guess_recipe_from_runner(runner, "runnable")
        recipe = self.get_data(recipe_file)
        if not recipe:
            self.cancel("Recipe file not found for this kind of runner")
        cmd = f"{runner} runnable-run-recipe {recipe}"
        result = process.run(cmd, ignore_status=True)
        self.assertEqual(result.exit_status, 0)

    def test_task_run_no_args(self):
        cmd = f"{self.get_runner()} task-run"
        result = process.run(cmd, ignore_status=True)
        self.assertEqual(result.exit_status, 2)

    def test_task_run_identifier_only(self):
        cmd = f"{self.get_runner()} task-run -i some_identifier"
        result = process.run(cmd, ignore_status=True)
        expected = int(self.params.get('task-run-id-only-exit-code',
                                       default=2))
        self.assertEqual(result.exit_status, expected)

    def test_task_run_recipe_no_args(self):
        """
        Makes sure the recipe argument is required
        """
        cmd = f"{self.get_runner()} task-run-recipe"
        result = process.run(cmd, ignore_status=True)
        self.assertEqual(result.exit_status, 2)

    def test_task_run_recipe_specific_kind(self):
        runner = self.get_runner()
        recipe_file = self.guess_recipe_from_runner(runner, "task")
        recipe = self.get_data(recipe_file)
        if not recipe:
            self.cancel("Recipe file not found for this kind of runner")
        cmd = f"{runner} task-run-recipe {recipe}"
        result = process.run(cmd, ignore_status=True)
        self.assertEqual(result.exit_status, 0)
