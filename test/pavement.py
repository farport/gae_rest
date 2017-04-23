# -*- coding: utf-8 -*-

'''
Paver based test runner that allow for dependencies based test.

The
'''

from __future__ import print_function

import sys
import os
from paver.easy import tasks, task, needs, consume_args, info, call_task

from testlib import TestRunner

# This is needed so paver can find sub modules
sys.path.insert(0, os.path.dirname(__file__))

TRUNNER = TestRunner()
ENV = tasks.Environment()


def task_exists(task_name):
    '''Check if task exists'''
    return not ENV.get_task(task_name) is None


@task
@needs(['corelib.default', 'test_models.default'])
def default():
    '''
    Run all the test that has been added into TestRunner.

    Note: TestRunner is a Singleton
    '''
    TRUNNER.run_added(failfast=True)
    info("Test completed")


@task
@consume_args
def run(options):
    '''
    Run a specific test
    '''
    run_tasks = True
    tasks_to_run = []
    for pkg in options.args:
        tname = None
        # check if task name exists if not try with .default
        if task_exists(pkg):
            tname = pkg
        else:
            default_name = "%s.default" % pkg
            if task_exists(default_name):
                tname = default_name
        if tname is None:
            print("task '%s' not found" % pkg)
            run_tasks = False
            break
        else:
            tasks_to_run.append(tname)
    if run_tasks:
        for tname in tasks_to_run:
            call_task(tname)
        TRUNNER.run_added(failfast=True)
        info("Test completed")
