'''
Tasks to execute the test
'''
from __future__ import print_function

from paver.easy import task, needs
from . import tests

import testlib

TRUNNER = testlib.TestRunner()


def getTaskFromCurrentPackage(task_name):
    return 'corelib.%s' % task_name


@task
def configuration_store():
    TRUNNER.add(tests.TestConfigurationStore)

# @needs([getTaskFromCurrentPackage('configuration_store')])
@task
@needs([getTaskFromCurrentPackage('configuration_store')])
def all():
    print("All tasks ran")

