'''
Tasks to execute the test
'''
from __future__ import print_function

from paver.easy import task, needs
from . import tests

import testlib

TRUNNER = testlib.TestRunner()


def getTasksFromCurrentPackage(*tasks):
    res = []
    for task in tasks:
        res.append('corelib.%s' % task)
    return res


@task
def test_configuration_store():
    TRUNNER.add(tests.TestConfigurationStore)

@task
def test_testlib():
    TRUNNER.add(tests.TestLibTests)

# @needs([getTaskFromCurrentPackage('configuration_store')])
@task
@needs(getTasksFromCurrentPackage('test_testlib', 'test_configuration_store'))
def all():
    print("All tasks ran")

