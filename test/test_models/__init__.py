'''
Tasks to execute the test
'''
from __future__ import print_function

from paver.easy import task, needs

import testlib
from . import test_simple

TRUNNER = testlib.TestRunner()


@task
def simple():
    TRUNNER.add(test_simple.SimpleNdbNestedTest)


@task
@needs('test_models.simple')
def all():
    print("All tasks ran")

