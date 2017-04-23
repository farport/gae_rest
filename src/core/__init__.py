# -*- coding: utf-8 -*-
'''
Created on 21 May 2013

@author: Marcos Lin

Provide core utilities objects for the app.
'''

from __future__ import print_function

import os
import sys
import logging
import json
import datetime


# ==============================================================================
# code debug print statement
import inspect

class Color(object): # pylint: disable=R0903
    '''Color for terminal constants'''
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DARKGRAY = '\033[90m'
    END = '\033[0m'


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
            caller = "%s:%s" % (inspect.stack()[1][3], inspect.stack()[1][2])
            # Convert all args into string
            msgs = []
            for arg in args:
                if isinstance(arg, basestring):
                    msgs.append(arg)
                else:
                    msgs.append(str(arg))
            print("%sT.%s: %s (%s)%s" % (Color.DARKGRAY, caller, ''.join(msgs), filename, Color.END))

def scream_print(*args):
    '''
    core.scream is used to print out text, mostly for debug purposes
    '''
    if __debug__:
        message = [Color.BOLD, Color.RED, "### "]
        message.extend(args)
        message.append(Color.END)
        print(''.join([str(x) for x in message]))


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
    DEFAULT_LOGGER_NAME = "ConfigurationStoreLogger"

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
        trace("_search_config called with in_caller_file=", in_caller_file, "; in_config_file=", in_config_file, ";in_local_name", in_local_name)

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
            trace("in_caller_file passed ", in_caller_file)
            if in_caller_file is None:
                # If in_caller_file is None, the config dir is expected to be located at
                # `../config` in relation to this file
                base_dir = os.path.join(os.path.dirname(__file__), "..")
            else:
                # If in_caller_file is passed, the config dir is expected to be located at
                # `./config` in relation to in_caller_file
                base_dir = os.path.dirname(in_caller_file)
            trace("base_dir set to ", base_dir)

            config_dir = os.path.join(base_dir, "config")

            # Search for the config file
            for file_name in ("dev.json", "qa.json", "uat.json", "prod.json", "app.json"):
                check_file = os.path.join(config_dir, file_name)
                trace("searching for the config file ", check_file)
                if os.path.exists(check_file):
                    config_file = os.path.realpath(check_file)
                    break

        trace("config_file set to:", config_file)
        trace("config_dir set to:", config_dir)

        # Set the local override file
        local_config = None
        if config_dir and os.path.isdir(config_dir):
            # Allow caller to override the name of the local file
            if in_local_name:
                local_name = in_local_name
            else:
                local_name = _default_local_name

            check_file = os.path.join(config_dir, local_name)
            trace("searching for the local file ", check_file)
            if os.path.isfile(check_file):
                local_config = os.path.realpath(check_file)

            cls._config_dir = os.path.realpath(config_dir)

            trace("local_config set to:", local_config)

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

    def __set_logger(self, in_logger=None):
        '''
        Set logger from logger passed, or created a new one using LOGGER_CONFIG entry.
        '''

        # Set or get a logger
        logger = None
        if in_logger:
            trace("Logger passed")
            logger = in_logger
        else:
            # Set the logger config params
            logger_name = self.DEFAULT_LOGGER_NAME
            log_level = logging.INFO
            logger_formatter = "%(asctime)-15s: [%(levelname)s] %(message)s [%(filename)s:%(lineno)d]"

            if hasattr(self, 'LOGGER_CONFIG'):
                trace("Reading logger info from config")
                cfg = getattr(self, 'LOGGER_CONFIG')

                # Get logger name from config or use the default name
                if cfg.get('name'):
                    logger_name = cfg['name']
                    trace("Logger name from config:", logger_name)

                # Read level from config or set to DEBUG
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
                    trace("Logger level from config:", config_level, "; value:", log_level)

                # Read the logging format string
                if "format" in cfg:
                    trace("Logger format from config:", format)
                    logger_formatter = cfg['format']

            # Force debug if __debug__ is set
            if sys.flags.debug:
                log_level = logging.DEBUG

            logger = logging.getLogger(logger_name)
            logger.propagate = False
            logger.setLevel(log_level)

            # Set format.  Support only STDOUT for now
            out_handler = logging.StreamHandler()
            out_handler.setLevel(log_level)
            formatter = logging.Formatter(logger_formatter)
            out_handler.setFormatter(formatter)
            logger.addHandler(out_handler)

        # Set logger name
        if 'LOGGER_NAME' not in self.__dict__:
            self.__dict__.update({'LOGGER_NAME': logger.name})

        self._logger = logger

    def __init__(self, in_caller_file=None, in_config_file=None, in_local_name=None, logger=None):
        '''
        Loads the json_file provided and, if exists, loads the override file named 'local.json'
        in the same directory as the json_file.

        If in_caller_file is passed, the expected the `config` dir would be at `./config` in
        relation to the file passed.  Otherwise, `config` dir should be located at `../config`
        of location of `core.__init__.py` file.
        '''
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
        self.__set_logger(logger)

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
        if ConfigurationStore.instance:
            if ConfigurationStore.instance._logger: # pylint: disable=W0212
                trace("Unloading ConfigurationStore loggers")
                ConfigurationStore.instance._logger.handlers = [] # pylint: disable=W0212
            ConfigurationStore.instance = None

    #
    # Allow the use of with statement
    #
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        pass
