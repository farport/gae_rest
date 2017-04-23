'''
Tasks to execute the test
'''
# pylint: disable=C0111

from paver.easy import task, needs

import testlib
from . import test_simple

TRUNNER = testlib.TestRunner()


@task
@needs('tcore.lib')
def nested():
    TRUNNER.add(test_simple.SimpleNdbNestedTest)


@task
@needs(testlib.gen_package_tasks(__name__, 'nested'))
def default():
    pass
