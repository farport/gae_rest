'''
Tasks to execute the test
'''
from __future__ import print_function

from paver.easy import task, needs
from . import tests

import testlib


def getTaskFromCurrentPackage(task_name):
    return 'corelib.%s' % task_name


@task
def configuration_store():
    testlib.run_tests([tests.TestConfigurationStore])

# @needs([getTaskFromCurrentPackage('configuration_store')])
@task
@needs([getTaskFromCurrentPackage('configuration_store')])
def all():
    print("All tasks ran")

