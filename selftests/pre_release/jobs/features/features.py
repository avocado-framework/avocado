#!/usr/bin/env python3

import glob
import os
import shutil
import sys

from avocado.core.job import Job

DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(DIR, 'tests')

FEAT_TESTS = [
    # job.run.result.html.enabled
    {'test_body_set_config': {'feature': 'job.run.result.html.enabled',
                              'value': 'on'},
     'test_body_job': {},
     'test_body_check_file': {'file': 'results.html',
                              'assert': 'self.assertTrue',
                              'assert_err': 'AssertTrue: could not find file %s'}
     },

    {'test_body_set_config': {'feature': 'job.run.result.html.enabled',
                              'value': 'off'},
     'test_body_job': {},
     'test_body_check_file': {'file': 'results.html',
                              'assert': 'self.assertFalse',
                              'assert_err': 'AssertFalse: found file %s'}
     },
    # job.run.result.json.enabled
    {'test_body_set_config': {'feature': 'job.run.result.json.enabled',
                              'value': 'on'},
     'test_body_job': {},
     'test_body_check_file': {'file': 'results.json',
                              'assert': 'self.assertTrue',
                              'assert_err': 'AssertTrue: could not find file %s'}
     },

    {'test_body_set_config': {'feature': 'job.run.result.json.enabled',
                              'value': 'off'},
     'test_body_job': {},
     'test_body_check_file': {'file': 'results.json',
                              'assert': 'self.assertFalse',
                              'assert_err': 'AssertFalse: found file %s'}
     },
    # job.run.result.tap.enabled
    {'test_body_set_config': {'feature': 'job.run.result.tap.enabled',
                              'value': 'on'},
     'test_body_job': {},
     'test_body_check_file': {'file': 'results.tap',
                              'assert': 'self.assertTrue',
                              'assert_err': 'AssertTrue: could not find file %s'}
     },

    {'test_body_set_config': {'feature': 'job.run.result.tap.enabled',
                              'value': 'off'},
     'test_body_job': {},
     'test_body_check_file': {'file': 'results.tap',
                              'assert': 'self.assertFalse',
                              'assert_err': 'AssertFalse: found file %s'}
     },
    # job.run.result.tap.include_logs
    {'test_body_set_config': {'feature': 'job.run.result.tap.include_logs',
                              'value': 'on'},
     'test_body_job': {},
     'test_body_check_file': {'file': 'results.tap',
                              'assert': 'self.assertTrue',
                              'assert_err': 'AssertTrue: could not find file %s'},
     'test_body_check_file_content': {'content': 'PASS 1-examples/tests/passtest.py:PassTest.test',}
     },
    # job.run.result.xunit.enabled
    {'test_body_set_config': {'feature': 'job.run.result.xunit.enabled',
                              'value': 'on'},
     'test_body_job': {},
     'test_body_check_file': {'file': 'results.xml',
                              'assert': 'self.assertTrue',
                              'assert_err': 'AssertTrue: could not find file %s'}
     },

    {'test_body_set_config': {'feature': 'job.run.result.xunit.enabled',
                              'value': 'off'},
     'test_body_job': {},
     'test_body_check_file': {'file': 'results.xml',
                              'assert': 'self.assertFalse',
                              'assert_err': 'AssertFalse: found file %s'}
     },

]


def load_templates():
    """
    Loads templates from files and returns a dictionary.
    """

    template_files = glob.glob(os.path.join(DIR, 'templates', '*.template'))

    templates = {}
    for template_file in template_files:
        with open(template_file, 'r') as f:
            template_name = os.path.basename(template_file)[:-9]
            templates[template_name] = f.read()

    return templates


if __name__ == '__main__':

    os.makedirs(TEST_DIR, exist_ok=True)
    templates = load_templates()

    references = []
    # build the tests
    for test in FEAT_TESTS:
        test_dict = {}
        feature = test['test_body_set_config']['feature'].replace('.', '_')
        value = test['test_body_set_config']['value']
        namespace = '%s_%s' % (feature, value)
        test_dict['class_name'] = feature
        test_dict['test_name'] = namespace
        test_dict['setup'] = templates['setup_create_tmpdir']

        # build the body
        body_list = []
        for code in test:
            body_list.append(templates[code].format(**test[code]))

        test_dict['test_body'] = ''.join(body_list)

        test_dict['tear_down'] = templates['teardown_clean_tmpdir']

        # save test to disk
        file_name = 'test_%s.py' % namespace
        with open(os.path.join(TEST_DIR, file_name), 'w') as f:
            f.write(templates['test_class'].format(**test_dict))
            references.append(f.name)

    # run all the tests
    config = {'run.references': references}
    with Job(config) as j:
        j.run()

    shutil.rmtree(TEST_DIR)
