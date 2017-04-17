'''
Created on 13 Sep 2016

@author: Marcos Lin

Load lib directory under src in sys.path
'''

from __future__ import print_function

import os
import sys
import unittest
import logging

def _initialize_lib():
    '''Add src folder'''
    src_dir = os.path.join(os.path.dirname(__file__), "..", "..", "src")
    sys.path.append(os.path.realpath(src_dir))

    # Setup logger for debug
    log_format = "%(asctime)-15s: [%(levelname)s] %(message)s [%(filename)s:%(lineno)d]"
    logging.basicConfig(level=logging.DEBUG, format=log_format)

_initialize_lib()

# Import from src
from core import Singleton


def run_tests(tcases, verbosity=2, failfast=True):
    testSuite = unittest.TestSuite()
    for tcase in tcases:
        print('''
#---------------------------------------------------------------------
# START UNIT TEST for '%s'
''' % tcase.__name__)

        testSuite.addTest(unittest.makeSuite(tcase))
        testRunner = unittest.TextTestRunner(verbosity=verbosity, failfast=failfast)
        testRunner.run(testSuite)


def app_enginge_init():
    '''Initialize app engine'''
    import dev_appserver
    dev_appserver.fix_sys_path()

    # Hack to solve the problem with 2 google packages
    file_dir = os.path.dirname(__file__)
    with open(os.path.join(file_dir, "..", "..", "venv", "lib", "python2.7", "site-packages", "google_appengine.pth")) as fh:
        for line in fh:
            appengine_sdk_path = line.rstrip()

    import google
    google.__path__.append(os.path.join(appengine_sdk_path, "google"))

    from google.appengine.ext import testbed
    from google.appengine.datastore import datastore_stub_util


class AppEngineTestbed(object):
    '''
    AppEngineTestbed is a Singleton to offer greater gradunality of control on
    type of datastore is needed for specific test.

    Every testbed is created for every `getTestPackage` via the `run_tests` method
    to guantee that testbed is reset (deactivated) at the end of every test module.

    This would also allow for a testCase inside a module to override the datastore
    mode as needed by calling AppEngineTestbed.unload() before creating a new instance.
    '''
    __metaclass__ = Singleton
    _testbed = None

    def __init__(self, datastore_mode='normal', show_message=True):
        if not datastore_mode or datastore_mode == 'none':
            return

        tb = testbed.Testbed()
        tb.activate()

        if show_message:
            print("\n# Testbest started with '%s' mode\n" % datastore_mode)

        if datastore_mode == "normal":
            tb.init_datastore_v3_stub()
        elif datastore_mode == "HR":
            # Test to High Replication mode with 100% percent probability of writes being applied
            # Ie: global query without ancestry should always return items after .put()
            # REF: https://cloud.google.com/appengine/docs/python/tools/localunittesting
            policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1)
            tb.init_datastore_v3_stub(consistency_policy=policy)
        elif datastore_mode == "HR_P0":
            # Test to High Replication mode with 0% percent probabily of writes being applied
            # Ie: global query without ancestry should never return items after .put()
            policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=0)
            tb.init_datastore_v3_stub(consistency_policy=policy)
        else:
            raise ValueError("Unsupported datastore_mode '%s'" % datastore_mode)

        # Prepare queue
        tb.init_taskqueue_stub(
            root_path=os.path.join(os.path.dirname(__file__), '../resources'))
        self.taskqueue_stub = tb.get_stub(testbed.TASKQUEUE_SERVICE_NAME)

        tb.init_memcache_stub()
        self._testbed = tb

    def deactivate(self):
        self.unload()

    @property
    def testbed(self):
        return self._testbed

    @classmethod
    def unload(cls):
        '''Setting the class' instance to None forcing the re-initialization.'''
        inst = AppEngineTestbed.instance
        if inst is not None:
            if inst._testbed is not None:
                # print "\n### DE-ACTIVATE and UNLOAD TESTBED ###\n"
                inst._testbed.deactivate()
            # else:
            #    print "\n### UNLOAD TESTBED ###\n"
            AppEngineTestbed.instance = None



'''
def run_tests(filename, test_pack, verbosity=2, failfast=True):
    datastore_mode = test_pack.get('datastore_mode')
    tests = test_pack['tests']

    testSuite = unittest.TestSuite()
    for test_case in tests:
        testSuite.addTest(unittest.makeSuite(test_case))

    testbed = AppEngineTestbed(datastore_mode, show_message=True)
    testRunner = unittest.TextTestRunner(verbosity=verbosity, failfast=failfast)
    testRunner.run(testSuite)
    testbed.unload()
'''

class DictToProperty(dict):
    def __init__(self, *args, **kwargs):
        super(DictToProperty, self).__init__(*args, **kwargs)
        protected = set(dir(dict))

        # Prevent the override of the dictionaries methods
        for key in self:
            if key in protected:
                raise ValueError("'%s' is a protected attribute and cannot be set" % key)

        self.__dict__ = self


class SharedTestData(DictToProperty):
    __metaclass__ = Singleton

    @classmethod
    def unload(cls):
        SharedTestData.instance = None
