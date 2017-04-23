'''
Tasks to execute the test
'''
# pylint: disable=C0111

from paver.easy import task, needs

import testlib
from . import tests

TRUNNER = testlib.TestRunner()


@task
def config():
    TRUNNER.add(tests.TestConfigurationStore)


@task
def lib():
    TRUNNER.add(tests.TestLibTests)


@task
@needs(testlib.gen_package_tasks(__name__, 'lib', 'config'))
def default():
    pass
