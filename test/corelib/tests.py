'''
Testing core library
'''

import unittest
import os

import testlib
from core import ConfigurationStore

SCRIPT_DIR = os.path.realpath(os.path.dirname(__file__))


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

if __name__ == '__main__':
    unittest.main(verbosity=2, failfast=True)
