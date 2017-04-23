'''
Created on 13 Sep 2016

@author: Marcos Lin

Load lib directory under src in sys.path
'''
# pylint: disable=C0111,C0413,E0401,W0201,W0212,R0903

from __future__ import print_function

import os
import sys
import json
import unittest
import logging
import StringIO

# Allow import from src
def _initialize_lib():
    '''Add src folder'''
    src_dir = os.path.join(os.path.dirname(__file__), "..", "..", "src")
    sys.path.append(os.path.realpath(src_dir))

    # Setup logger for debug
    log_format = "%(asctime)-15s: [%(levelname)s] %(message)s [%(filename)s:%(lineno)d]"
    logging.basicConfig(level=logging.DEBUG, format=log_format)

_initialize_lib()

# Basic init for app engine
from core import Singleton # pylint: disable=
# Make App Enginge Works
import dev_appserver
dev_appserver.fix_sys_path()

# Import Google packages
def _google_package_hack():
    '''Hack to solve the problem with 2 google packages'''
    file_dir = os.path.dirname(__file__)
    with open(os.path.join(file_dir, "..", "..", "venv", "lib", "python2.7", "site-packages", "google_appengine.pth")) as _:
        for line in _:
            appengine_sdk_path = line.rstrip()
    google.__path__.append(os.path.join(appengine_sdk_path, "google"))

import google
_google_package_hack()
from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util


class TestRunner(object):
    __metaclass__ = Singleton

    @classmethod
    def _log_test(cls, test_case, mode):
        if mode:
            message = "UNIT TEST for '%s' with datastore mode of '%s" % (test_case.__name__, mode)
        else:
            message = "UNIT TEST for '%s'" % test_case.__name__

        print('''
#---------------------------------------------------------------------
# %s
''' % message)

    @classmethod
    def run(cls, test_case, verbosity=2, failfast=True):
        '''Run one test case at a time'''
        gaetest = AppEngineTestbed()

        # Set datastore_mode if needed
        if hasattr(test_case, 'datastore_mode'):
            mode = test_case.datastore_mode
            cls._log_test(test_case, mode)
            gaetest.set_mode(mode)
        else:
            cls._log_test(test_case, None)

        runner = unittest.TextTestRunner(verbosity=verbosity, failfast=failfast)
        return runner.run(unittest.makeSuite(test_case)).wasSuccessful()

    @classmethod
    def run_all(cls, test_cases, test_name=None, verbosity=2, failfast=True):
        '''Pass a list of test cases and call .run method'''
        tests_ran = 0
        for tcase in test_cases:
            if test_name is None:
                run_ok = cls.run(tcase, verbosity, failfast)
                tests_ran += 1
            else:
                # Only run if test_name matches
                if test_name in tcase.__name__:
                    run_ok = cls.run(tcase, verbosity, failfast)
                    tests_ran += 1
                else:
                    # Just assumed that test ran ok
                    run_ok = True
            if failfast and not run_ok:
                break

        return tests_ran

    def __init__(self):
        self._tcases = []

    def add(self, test_case):
        '''Store the test case passed to be ran later with .run_added'''
        self._tcases.append(test_case)

    def run_added(self, test_name=None, verbosity=2, failfast=True):
        '''Run stored test cases'''
        return self.run_all(self._tcases, test_name, verbosity, failfast)


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
    _datastore_mode = None

    def __set_datastore_mode(self, mode, show_message):
        tbed = self._testbed

        if mode is None:
            tbed.deactivate()
            if show_message:
                print("\n# Testbest deactivated")
        else:
            tbed.activate()
            if mode == "normal":
                tbed.init_datastore_v3_stub()
            elif mode == "HR":
                # Test to High Replication mode with 100% percent probability of writes being applied
                # Ie: global query without ancestry should always return items after .put()
                # REF: https://cloud.google.com/appengine/docs/python/tools/localunittesting
                policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1)
                tbed.init_datastore_v3_stub(consistency_policy=policy)
            elif mode == "HR_P0":
                # Test to High Replication mode with 0% percent probabily of writes being applied
                # Ie: global query without ancestry should never return items after .put()
                policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=0)
                tbed.init_datastore_v3_stub(consistency_policy=policy)
            else:
                raise ValueError("Unsupported datastore_mode '%s'" % mode)

            if show_message:
                print("\n# Testbest started with '%s' mode\n" % mode)

            # Prepare queue
            tbed.init_taskqueue_stub(
                root_path=os.path.join(os.path.dirname(__file__), '../resources'))
            self.taskqueue_stub = tbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)

            # Prepare memcache
            tbed.init_memcache_stub()


    def set_mode(self, mode, show_message=False):
        '''
        Check if datastore_mode needs to be changed
        '''

        mode_changed = False

        # Data cleanup
        if mode == 'none':
            mode = None

        # Change detection
        if self._datastore_mode is None and mode is None:
            mode_changed = False
        elif self._datastore_mode is not None and mode is None:
            mode_changed = True
        elif self._datastore_mode is None and mode is not None:
            mode_changed = True
        elif self._datastore_mode == mode:
            mode_changed = False
        else:
            mode_changed = True

        if mode_changed:
            self.__set_datastore_mode(mode, show_message)
            self._datastore_mode = mode

    def __init__(self):
        self._testbed = testbed.Testbed()

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
            if cls._datastore_mode:
                # print "\n### DE-ACTIVATE and UNLOAD TESTBED ###\n"
                inst._testbed.deactivate()
            # else:
            #    print "\n### UNLOAD TESTBED ###\n"
            AppEngineTestbed.instance = None


# DATA RELATED
class JsonDataReader(object):
    '''
    Read the JSON from the data directory returning DictToProperty object
    '''
    def __init__(self, script_file=None):
        if script_file is None:
            script_file = __file__
        data_dir = os.path.join(os.path.dirname(script_file), 'data')
        if os.path.isdir(data_dir):
            self._data_dir = os.path.realpath(data_dir)
        else:
            raise IOError("Required directory not found: %s" % data_dir)

    def get(self, *paths):
        '''
        Return the json data if file ends with json.  Otherwise, return the content.
        '''
        data_file = os.path.join(self._data_dir, *paths)
        with open(data_file, "r") as _:
            if data_file.endswith(".json"):
                data = json.load(_)
                return EasyAccessDict(data)

            return _.read()


class EasyAccessDict(dict):
    def __init__(self, *args, **kwargs):
        super(EasyAccessDict, self).__init__(*args, **kwargs)
        self._protected_properties = set(dir(dict))

    def _get_elem(self, mode, *keys):
        '''
        Returns a tuple of penultimate element and the final key in JSON as specified using input keys
        array that defines the path.  If any element of the path does not exists, create it.
        The return tuple allow the final element to be set or deleted
        mode can be `get` or `set`
        '''
        key_list = list(keys)
        last_key = key_list.pop()
        elem = self

        for key in key_list:
            if key not in elem:
                if mode == 'get':
                    return None, None
                else:
                    elem[key] = {}
            elem = elem[key]

        return elem, last_key

    def get(self, *keys):
        '''Return element given the path'''
        if keys:
            elem, key = self._get_elem('get', *keys)
            if elem:
                if key in elem:
                    return elem[key]

    def set(self, value, *keys):
        '''Set the value for the given path'''
        elem, key = self._get_elem('set', *keys)
        elem[key] = value

    def delete(self, *keys):
        '''Delete the key for the given path'''
        elem, key = self._get_elem('get', *keys)
        if elem:
            del elem[key]

    def json_text(self, *keys, **kwargs):
        '''Return the json text'''
        if keys:
            json_data = self.get(*keys)
        else:
            json_data = self
        if 'indent' not in kwargs:
            kwargs['indent'] = 4
        return json.dumps(json_data, **kwargs)


class SharedTestData(EasyAccessDict):
    '''Data that can be share between tests'''
    __metaclass__ = Singleton

    @classmethod
    def unload(cls):
        '''Unload and clear the shared data'''
        SharedTestData.instance = None


class CaptureLogger(object):
    '''
    Used to capture the output of logger.  Calling get return a dictionary of level and message.
    '''
    RECORD_SEPARATOR = "|"
    def __init__(self, logger, level=None):
        self._io = StringIO.StringIO()
        stream_handler = logging.StreamHandler(self._io)

        if level is None:
            level = logging.DEBUG
        stream_handler.setLevel(level)
        formatter = logging.Formatter("%(levelname)s" + self.RECORD_SEPARATOR + "%(message)s")
        stream_handler.setFormatter(formatter)

        logger.addHandler(stream_handler)

    def get(self):
        '''Return a list of level and message logged'''
        result = []
        content = self._io.getvalue()
        if content:
            for line in content.split(os.linesep):
                if line:
                    if self.RECORD_SEPARATOR in line:
                        level, message = line.split(self.RECORD_SEPARATOR, 1)
                    else:
                        level = None
                        message = line

                    result.append({
                        "level": level,
                        "message": message
                    })
        self._io.truncate(0)

        return result

# Paver based tasks related utilities
def gen_package_tasks(pkg_name, *task_names):
    result = []
    for tname in task_names:
        result.append("%s.%s" % (pkg_name, tname))
    return result
