'''
Tasks to execute the test
'''
# pylint: disable=C0111

from paver.easy import task, needs

import testlib
from . import test_simple, test_parser, test_view

TRUNNER = testlib.TestRunner()


@task
@needs('tcore.lib')
def nested():
    TRUNNER.add(test_simple.SimpleNdbNestedTest)


@task
@needs('tcore.lib')
def parser():
    TRUNNER.add(test_parser.ModelParserTest)

@task
@needs('tcore.lib')
def view():
    TRUNNER.add(test_view.ViewTest)


@task
@needs(testlib.gen_package_tasks(__name__, 'nested', 'parser', 'view'))
def default():
    pass
