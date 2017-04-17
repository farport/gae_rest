# -*- coding: utf-8 -*-
'''
Created on 21 May 2013

@author: Marcos Lin

Provide core utilities objects for the app.
'''

from __future__ import print_function

import os
import sys
import inspect
import logging
import json

import time
import datetime
import random
import hashlib
import base64


# ==============================================================================
# code debug print statement
def trace(*args):
    '''
    core.trace is light weight debug statement to be used for code that imports this package.
    To minimize unnecessary processing, make sure to pass a tuple of string to be joined upon
    trace output instead of creating the final string on the caller side.

    For trace statement in a heavily used code and/or loop, make sure to precede the trace
    statement with a 'if __debug__:' check allowing entire trace statement to be compiled out.
    In fact, if this module is compiled with optimization, trace will stop working.
    '''
    if __debug__:
        if sys.flags.debug:
            filename = os.path.basename(inspect.stack()[1][1])
            caller = inspect.stack()[1][3]
            # Convert all args into string
            msgs = []
            for arg in args:
                if isinstance(arg, basestring):
                    msgs.append(arg)
                else:
                    msgs.append(str(arg))
            print("T.%s: %s (%s)" % (caller, ''.join(msgs), filename))


# ==============================================================================
# Singletons
class Singleton(type):
    '''
    Meta Class used to create a singleton.  Usage:

    def ClassObject(object):
        __metaclass__ = Singleton
        ...
    '''
    def __init__(cls, name, bases, dct):
        # print("### Singleton called for class %s" % name)
        super(Singleton, cls).__init__(name, bases, dct)
        cls.instance = None

    def __call__(cls, *args, **kwargs):
        if cls.instance is None:
            # print("### New Instance of %s" % cls.__name__)
            # print("### dir: %s" % ','.join([x for x in cls.__dict__]))
            cls.instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.instance


# ==============================================================================
# Config
class ConfigurationStore(object):
    '''
    Loads a json file and set all keys to be property of this object.  This is can used by
    Flask's configuration system '.config.from_object(<obj>)' that will read all UPPER CASE
    property of this and expose it via '.config["<key>"]' method.

    Key properties of this config:
    * APP: name of the application
    * INST: physical server location of deployed app
    * RUN_MODE: prod, qa, test, dev or utest

    By default, this object will look for an additional configuration, in the same directory
    as the configuration file provided, named 'local.json'.  This is to allow local development
    override.
    '''
    __metaclass__ = Singleton
    _logger = None

    @classmethod
    def _search_config(cls, in_caller_file=None, in_config_file=None, in_local_name=None):
        '''
        This method searches for file in the ../config directory from the current script directory
        in the following order:
           a. dev.json
           b. qa.json
           c. uat.json
           d. prod.json
           e. app.json

        The @classmethod decoration created only for unit testing purpose
        '''

        _default_local_name = "local.json"

        # Set the config file
        config_file = None
        config_dir = None
        if in_config_file:
            # If config file is passed, the config directory is the dir of the config file
            if os.path.isfile(in_config_file):
                config_file = os.path.realpath(in_config_file)
                config_dir = os.path.dirname(config_file)
        else:
            if in_caller_file is None:
                # If in_caller_file is None, the config dir is expected to be located at
                # `../config` in relation to this file
                base_dir = os.path.join(os.path.dirname(__file__), "..")
            else:
                # If in_caller_file is passed, the config dir is expected to be located at
                # `./config` in relation to in_caller_file
                base_dir = os.path.dirname(in_caller_file)

            config_dir = os.path.join(base_dir, "config")

            # Search for the config file
            for file_name in ("dev.json", "qa.json", "uat.json", "prod.json", "app.json"):
                check_file = os.path.join(config_dir, file_name)
                if os.path.exists(check_file):
                    config_file = os.path.realpath(check_file)
                    break

        # Set the local override file
        local_config = None
        if config_dir and os.path.isdir(config_dir):
            # Allow caller to override the name of the local file
            if in_local_name:
                local_name = in_local_name
            else:
                local_name = _default_local_name

            check_file = os.path.join(config_dir, local_name)
            if os.path.isfile(check_file):
                local_config = os.path.realpath(check_file)

            cls._config_dir = os.path.realpath(config_dir)

        return config_file, local_config

    def __apply_json_config(self, json_file):
        '''
        Open the json file and make the key become the attribute of the object,
        ignoring the keys starting with '_'
        '''
        json_data = self.load_json_file(json_file)
        for key in json_data:
            if not key.startswith("_"):
                self.__dict__.update({key: json_data[key]})

    def __set_default_config_value(self, key, default_value):
        if key not in self.__dict__:
            self.__dict__[key] = default_value

    def __init__(self, in_caller_file=None, in_config_file=None, in_local_name=None, logger=None):
        '''
        Loads the json_file provided and, if exists, loads the override file named 'local.json'
        in the same directory as the json_file.

        If in_caller_file is passed, the expected the `config` dir would be at `./config` in
        relation to the file passed.  Otherwise, `config` dir should be located at `../config`
        of location of `core.__init__.py` file.
        '''
        if logger:
            self._logger = logger

        # Search for configuration file
        config_file, local_config = self._search_config(in_caller_file, in_config_file, in_local_name)

        if config_file:
            self.__apply_json_config(config_file)

        if local_config:
            self.__apply_json_config(local_config)

        # Set the default, expected value
        self.__set_default_config_value('APP', None)
        self.__set_default_config_value('INST', None)
        self.__set_default_config_value('RUN_MODE', 'dev')

        # Set logger
        self.set_logger()

    @property
    def config_dir(self):
        '''
        Return the config directory
        '''
        return self._config_dir

    @property
    def logger(self):
        '''Return logger.  Create one if not set'''
        return self._logger

    def set_logger(self, in_logger=None):
        '''
        Set logger from logger passed, or created a new one using LOGGER_CONFIG entry.
        '''

        # Set or get a logger
        logger = None
        if in_logger:
            logger = in_logger
            self.__dict__.update({'LOGGER_NAME': logger.name})
        else:
            if hasattr(self, "LOGGER_NAME"):
                logger = logging.getLogger(getattr(self, "LOGGER_NAME"))

            if hasattr(self, 'LOGGER_CONFIG'):
                cfg = getattr(self, 'LOGGER_CONFIG')
                logger = logging.getLogger(cfg['name'])
                logger.propagate = False

                # Set level
                if 'level' in cfg:
                    # Translate string level to constant value
                    config_level = cfg['level']
                    levels = {
                        'debug': logging.DEBUG,
                        'info': logging.INFO,
                        'warning': logging.WARNING,
                        'error': logging.ERROR,
                        'critical': logging.CRITICAL
                    }
                    log_level = levels.get(config_level, logging.NOTSET)
                    logger.setLevel(log_level)

                # Set format.  Support only STDOUT for now
                out_handler = logging.StreamHandler()
                out_handler.setLevel(log_level)
                if "format" in cfg:
                    formatter = logging.Formatter(cfg['format'])
                    out_handler.setFormatter(formatter)
                logger.addHandler(out_handler)

        self._logger = logger

    @classmethod
    def load_json_file(cls, json_file):
        '''Load json file and return a dictionary'''
        if not os.path.exists(json_file):
            raise IOError("Failed to load '%s' json file as it does not exists." % json_file)
        with open(json_file, "r") as _:
            try:
                return json.load(_)
            except ValueError as err:
                raise IOError("Failed to parse '%s' as json.  Error: %s" % (json_file, err))

    @classmethod
    def unload(cls):
        '''Setting the class' instance to None forcing the re-initialization.'''
        trace("Unloading ConfigurationStore")
        cls._config_dir = None
        ConfigurationStore.instance = None

    #
    # Allow the use of with statement
    #
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        pass
