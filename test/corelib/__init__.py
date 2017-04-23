'''
Tasks to execute the test
'''
# pylint: disable=C0111

from __future__ import print_function

from paver.easy import task, needs

import testlib
from . import tests

TRUNNER = testlib.TestRunner()

def gen_tasks_from_current_package(*tasks):
    '''Prepend the package name'''
    res = []
    for _ in tasks:
        res.append('corelib.%s' % _)
    return res


@task
def config():
    TRUNNER.add(tests.TestConfigurationStore)


@task
def lib():
    TRUNNER.add(tests.TestLibTests)


@task
@needs(gen_tasks_from_current_package('lib', 'config'))
def default():
    pass
