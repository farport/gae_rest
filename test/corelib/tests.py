'''
Testing core library
'''

import unittest
import os
import logging

import testlib
from core import ConfigurationStore

SCRIPT_DIR = os.path.realpath(os.path.dirname(__file__))
READER = testlib.JsonDataReader(__file__)

class TestLibTests(unittest.TestCase):
    '''
    Test for testlib

    Note: although the test focus on EasyAccessDict, JsonDataReader is also being tested
    '''
    def setUp(self):
        self.data = READER.get("test.json")

    def test01_easy_dict(self):
        '''
        Test that EasyAccessDict can be accessed as a dict and that content is as expected.
        Also test that JsonDataReader returns the right data
        '''
        # This should be exact replica of what's in test.sjon
        ref_dict = {
            "level": 1,
            "ref": "level 1",
            "level2": {
                "level": 2,
                "ref": "level 2",
                "level3": {
                    "level": 3,
                    "ref": "level 3",
                    "content": {
                        "level": 4,
                        "ref": "level 4"
                    }
                }
            }
        }
        self.assertDictEqual(self.data, ref_dict)

    def test02_easy_dict_get(self):
        '''Make sure multi-level get works'''
        self.assertEqual(self.data.get("level2", "ref"), "level 2")
        self.assertEqual(self.data["level2"]["ref"], "level 2")

        self.assertEqual(self.data.get("level2", "level3", "ref"), "level 3")
        self.assertEqual(self.data["level2"]["level3"]["ref"], "level 3")

        self.assertEqual(self.data.get("level2", "level3", "content", "level"), 4)
        self.assertEqual(self.data["level2"]["level3"]["content"]["level"], 4)

    def test03_easy_dict_get_error(self):
        '''Make sure error are consistant.  Get will not raise the error but return None'''
        self.assertIsNone(self.data.get("level2", "level3", "wrong_key"))
        try:
            _ = self.data["level2"]["level3"]["wrong_key"]
        except StandardError as ex:
            self.assertIsInstance(ex, KeyError)

        self.assertIsNone(self.data.get("level2", "ref", "wrong_key"))
        try:
            _ = self.data["level2"]["ref"]["wrong_key"]
        except StandardError as ex:
            self.assertIsInstance(ex, TypeError)

    def test04_easy_dict_set(self):
        '''Make sure multi-level set works'''
        attrs = ("level2", "content")
        s = "level 2 content"

        # level2.content should not exists
        self.assertIsNone(self.data.get(*attrs))
        try:
            _ = self.data["level2"]["content"]
        except StandardError as ex:
            self.assertIsInstance(ex, KeyError)

        # Set and check for level2.content
        self.data.set(s, *attrs)
        self.assertEqual(self.data.get(*attrs), s)
        self.assertEqual(self.data["level2"]["content"], s)

    def test05_easy_dict_delete(self):
        '''Make sure that delete works'''
        attrs = ("level2", "level3", "content")

        # level2.level3.content should exists
        self.assertIsNotNone(self.data.get(*attrs))

        # Set and check for level2.content
        self.data.delete(*attrs)
        self.assertIsNone(self.data.get(*attrs))

    def test06_easy_dict_json_text(self):
        '''Make sure that json output works as expected,  also test that JsonDataReader returns non json data'''
        expected_all = READER.get("test_json_text_all.txt")
        self.assertEqual(self.data.json_text(indent=None), expected_all)

        expected_level3 = READER.get("test_json_text_level3.txt")
        self.assertEqual(self.data.json_text("level2", "level3", indent=None), expected_level3)



class TestConfigurationStore(unittest.TestCase):
    '''
    Testing core.ConfigurationStore.  The testing directory is set to the `config` dir
    because the normal dir would actually be `core`, which is located at the same
    '''

    def _get_path(self, *dirs):
        if dirs:
            result = os.path.realpath(os.path.join(SCRIPT_DIR, *dirs))
        else:
            result = SCRIPT_DIR
        return result

    def test01_simple(self):
        '''Simple test without any param'''
        config_file, local_file = ConfigurationStore._search_config()

        self.assertIsNone(config_file)
        self.assertIsNone(local_file)

    def test02_conf_store_dev(self):
        '''Testing simple dev.json'''
        target_dir = self._get_path('conf_store_dev', 'config')
        config_file, local_file = ConfigurationStore._search_config(in_caller_file=target_dir)

        self.assertEqual(config_file, os.path.join(target_dir, 'dev.json'))
        self.assertIsNone(local_file)

    def test03_conf_store_qa(self):
        '''Testing simple qa.json'''
        target_dir = self._get_path('conf_store_qa', 'config')
        config_file, local_file = ConfigurationStore._search_config(in_caller_file=target_dir)

        self.assertEqual(config_file, os.path.join(target_dir, 'qa.json'))
        self.assertIsNone(local_file)

    def test04_conf_store_uat(self):
        '''Testing simple uat.json'''
        target_dir = self._get_path('conf_store_uat', 'config')
        config_file, local_file = ConfigurationStore._search_config(in_caller_file=target_dir)

        self.assertEqual(config_file, os.path.join(target_dir, 'uat.json'))
        self.assertIsNone(local_file)

    def test05_conf_store_uat(self):
        '''Testing uat.json with local name'''
        target_dir = self._get_path('conf_store_uat', 'config')
        config_file, local_file = ConfigurationStore._search_config(in_caller_file=target_dir, in_local_name="conf_local.json")

        self.assertEqual(config_file, os.path.join(target_dir, 'uat.json'))
        self.assertEqual(local_file, os.path.join(target_dir, 'conf_local.json'))

    def test06_conf_store_prod(self):
        '''Testing simple prod.json and local.json'''
        target_dir = self._get_path('conf_store_prod', 'config')
        config_file, local_file = ConfigurationStore._search_config(in_caller_file=target_dir)

        self.assertEqual(config_file, os.path.join(target_dir, 'prod.json'))
        self.assertEqual(local_file, os.path.join(target_dir, 'local.json'))

    def test07_conf_store_prod_config_file(self):
        '''Testing passing a config file'''
        forced_conf_file = self._get_path('conf_store_prod', 'conf.json')
        config_file, local_file = ConfigurationStore._search_config(in_config_file=forced_conf_file)

        self.assertEqual(config_file, forced_conf_file)
        self.assertIsNone(local_file)

    def test08_conf_store_prod_local_file(self):
        '''Setting a local name'''
        forced_conf_file = self._get_path('conf_store_prod', 'conf.json')
        config_file, local_file = ConfigurationStore._search_config(in_config_file=forced_conf_file, in_local_name="prod_local.json")

        self.assertEqual(config_file, forced_conf_file)
        self.assertEqual(local_file, self._get_path('conf_store_prod', 'prod_local.json'))

    def test10_conf_store(self):
        '''Testing passing a config file to ConfigurationStore with local override'''
        ConfigurationStore.unload()
        conf = ConfigurationStore()

        self.assertIsNone(conf.config_dir)
        self.assertIsNone(conf.APP)
        self.assertIsNone(conf.INST)
        self.assertEqual(conf.RUN_MODE, "dev")

        # Not using assertRaises as DATA is a property and not a function
        try:
            _ = conf.DATA
            exceptionRaised = False
        except AttributeError:
            exceptionRaised = True
        self.assertTrue(exceptionRaised, "Expected AttributeError for conf.DATA")

    def test11_conf_store_conf(self):
        '''Testing passing a config file to ConfigurationStore with local override'''
        ConfigurationStore.unload()
        conf = ConfigurationStore(__file__)

        self.assertEqual(conf.config_dir, self._get_path('config'))
        self.assertEqual(conf.APP, "Config for app.json")
        self.assertEqual(conf.DATA, "override by local.json")
        self.assertEqual(conf.LOCAL_INFO, "local info")

    def test12_conf_store_conf_local(self):
        '''Testing passing a config file to ConfigurationStore with local name override'''
        ConfigurationStore.unload()
        conf = ConfigurationStore(__file__, in_local_name="app_local.json")

        self.assertEqual(conf.config_dir, self._get_path('config'))
        self.assertEqual(conf.APP, "Config for app.json")
        self.assertEqual(conf.DATA, "override by app_local.json")

        # Not using assertRaises as LOCAL_INFO is a property and not a function
        try:
            _ = conf.LOCAL_INFO
            exceptionRaised = False
        except AttributeError:
            exceptionRaised = True
        self.assertTrue(exceptionRaised, "Expected AttributeError for conf.LOCAL_INFO")

    def test20_conf_store_logger(self):
        '''Make sure that CaptureLogger works and that default logger is created correctly by ConfigurationStore'''
        with ConfigurationStore() as c:
            logger = c.logger
        clog = testlib.CaptureLogger(logger)

        # Check name of the logger
        self.assertEqual(logger.name, ConfigurationStore.DEFAULT_LOGGER_NAME)
        self.assertEqual(logger.level, logging.INFO)

        # Level is INFO so debug should't log
        logger.debug("This is debug")
        expected = []
        self.assertListEqual(expected, clog.get())

        # Make sure logging works
        logger.info("This is info")
        logger.warn("A warning message")
        logger.error("A error occurred")
        expected = [
            {"level": "INFO", "message": "This is info"},
            {"level": "WARNING", "message": "A warning message"},
            {"level": "ERROR", "message": "A error occurred"}
        ]
        self.assertListEqual(expected, clog.get())

        logger.critical("Not a good thing...")
        expected = [{"level": "CRITICAL", "message": "Not a good thing..."}]
        self.assertListEqual(expected, clog.get())

        ConfigurationStore.unload()

    def test21_conf_store_logger_config(self):
        '''Make sure that logger is create correctly from config file'''
        with ConfigurationStore(__file__, in_local_name="logger_local.json") as c:
            logger = c.logger

        self.assertEqual(logger.name, "TestLogger")
        self.assertEqual(logger.level, logging.CRITICAL)
        self.assertEqual(len(logger.handlers), 1)

        handler = logger.handlers[0]
        self.assertEqual(handler.formatter._fmt, "%(asctime)-15s:|%(levelname)s|%(message)s|%(filename)s|%(lineno)d")


if __name__ == '__main__':
    unittest.main(verbosity=2, failfast=True)
