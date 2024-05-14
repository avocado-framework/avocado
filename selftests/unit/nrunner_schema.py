import glob
import json
import os

from avocado import Test, skipUnless
from selftests.utils import BASEDIR

try:
    import jsonschema

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


BASE_SCHEMA_DIR = os.path.join(BASEDIR, "avocado", "schemas")
BASE_RECIPE_DIR = os.path.join(BASEDIR, "examples", "nrunner", "recipes")


@skipUnless(JSONSCHEMA_AVAILABLE, "jsonschema module not available")
class Schema(Test):
    def _test(self, schema_filename, recipe_path):
        schema_path = os.path.join(BASE_SCHEMA_DIR, schema_filename)
        with open(schema_path, "r", encoding="utf-8") as schema:
            with open(recipe_path, "r", encoding="utf-8") as recipe:
                try:
                    jsonschema.validate(json.load(recipe), json.load(schema))
                except jsonschema.exceptions.ValidationError as details:
                    self.fail(details)

    def test_runnable_recipes(self):
        for recipe_path in glob.glob(
            os.path.join(BASE_RECIPE_DIR, "runnable", "*.json")
        ):
            self._test("runnable-recipe.schema.json", recipe_path)
