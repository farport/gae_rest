'''
Tasks to execute the test
'''
# pylint: disable=C0111

from __future__ import print_function

from paver.easy import task, needs

import testlib
from . import test_simple

TRUNNER = testlib.TestRunner()


@task
@needs('corelib.lib')
def nested():
    TRUNNER.add(test_simple.SimpleNdbNestedTest)


@task
@needs('test_models.nested')
def default():
    pass
