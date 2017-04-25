'''
Tasks to execute the route tests
'''
# pylint: disable=C0111

from paver.easy import task, needs

import testlib
from . import tests

TRUNNER = testlib.TestRunner()


@task
def app():
    TRUNNER.add(tests.AppRouteTest)


@task
def blueprint():
    TRUNNER.add(tests.BlueprintRouteTest)


@task
@needs(testlib.gen_package_tasks(__name__, 'app', 'blueprint'))
def default():
    pass
