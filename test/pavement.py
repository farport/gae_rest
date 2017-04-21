# -*- coding: utf-8 -*-

'''
Test runner
'''

from __future__ import print_function

import sys
import os
from paver.easy import task, needs, consume_args

from testlib import TestRunner

# This is needed so paver can find sub modules
sys.path.insert(0, os.path.dirname(__file__))

@task
@needs(['corelib.all', 'test_models.all'])
def default():
    '''
    Run all the test that has been added into TestRunner.

    Note: TestRunner is a Singleton
    '''
    trunner = TestRunner()
    trunner.run_added(failfast=True)
    print("Test completed")


@task
@consume_args
def test(options):
    '''
    Run a specific test
    '''
    print("This is test tasks")
    print("options: %s" % options.args)
