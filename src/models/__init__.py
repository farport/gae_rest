'''
ndb.Model related utilities

by: marcos.lin@farport.co
on: 23 April 2017

NdbUtilMixIn has the following focus:
* Facilitate setting of a ndb.Model from a dictionary
* Create a dictionary for output to JSON
* Provide a standard by of converting value to and from model and dictionary

'''
# pylint: disable=W0212

from __future__ import print_function

import copy
import datetime

from google.appengine.ext import ndb

from google.net.proto.ProtocolBuffer import ProtocolBufferDecodeError
from google.appengine.api.datastore_errors import Error, BadValueError

from core import ConfigurationStore

with ConfigurationStore() as c:
    LOGGER = c.logger

# ==============================================================================
# Define Exceptions
#
class NdbModelError(Error):
    '''Generic and base error used by NdbUtilMixIn object'''
    pass

class NdbModelMismatchError(NdbModelError):
    '''When updating model with a key but entity returned is of different model'''
    pass

class NdbModelInitializationError(NdbModelError):
    '''Error while trying to initialize a model with NdbUtilMixIn'''
    pass

class DuplicateEntryError(NdbModelError):
    '''Exception due to _unique_properties'''
    pass

class ParserConversionError(NdbModelError):
    '''Error when value conversion fails in ModelParser'''
    def __init__(self, in_message, ex):
        if isinstance(ex, Exception):
            message = "%s.  %s: %s" % (in_message, ex.__class__.__name__, ex)
        else:
            message = in_message
        super(ParserConversionError, self).__init__(message)

class InvalidValueError(NdbModelError, BadValueError):
    '''Generic ValueError'''
    pass

class InvalidKeyError(InvalidValueError):
    '''key passed is not a valid ndb.Key'''
    def __init__(self, in_key=None, message=None):
        if message is None:
            if in_key is None:
                message = "A 'None' value passed as key"
            else:
                message = "Key '%s' of type '%s' is not a valid key" % (in_key, type(in_key))
        super(InvalidKeyError, self).__init__(message)

class MissingRequiredPropertyError(InvalidValueError):
    '''Exception due to _required_properties'''
    def __init__(self, *prop_names):
        if len(prop_names) == 1:
            message = "Required property '%s' is not set." % prop_names
        elif len(prop_names) > 1:
            message = "Required properties '%s' are not set." % ",".join(["'%s'" % x for x in prop_names])
        else:
            raise NdbModelError("UninitializedRequiredPropertyError error received no property name")
        super(MissingRequiredPropertyError, self).__init__(message)

class PutMethodDisabledError(NdbModelError):
    '''Raised when put method of a ndb.Model is disabled intentionally (StubModel)'''
    def __init__(self, object_classname, alternative_put_method_name=None):
        if object_classname:
            message = "%s object must be persisted using the %s method" % (object_classname, alternative_put_method_name)
        else:
            message = "%s object cannot be saved"
        super(PutMethodDisabledError, self).__init__(message)



# ==============================================================================
# ndb.Model related
#
class ModelParser(object):
    '''
    This class focus on converting dictionary to and from a ndb model.  It takes care
    of conversion via the following 2 method that is designed to be overriden:

        * value_for_property
        * text_from_property

    By default, following conversions are built in:

        * DateProperty to string
        * DateTimeProperty to string
        * KeyProperty to base64 string
    '''

    @classmethod
    def decode_ndb_key(cls, in_key, raise_exception=False):
        '''
        Convert the input key into ndb.Key, ignoring any exception decoding urlsafe string.

        raises InvalidKeyError if raise_exception set to True.
        '''
        if in_key is None:
            if raise_exception:
                raise InvalidKeyError(in_key)
            res = None
        elif isinstance(in_key, ndb.Key):
            res = in_key
        elif isinstance(in_key, basestring):
            # Fix per: https://github.com/googlecloudplatform/datastore-ndb-python/issues/143
            try:
                res = ndb.Key(urlsafe=in_key)
            except ProtocolBufferDecodeError:
                if raise_exception:
                    raise InvalidKeyError(in_key)
            except StandardError as ex:
                if ex.__class__.__name__ == 'ProtocolBufferDecodeError':
                    if raise_exception:
                        raise InvalidKeyError(in_key)
                else:
                    raise
        else:
            if raise_exception:
                raise InvalidKeyError(in_key)

        return res

    def __init__(self, model):
        self._model = model

    def _get_property_from_model_by_name(self, model, name):
        if not isinstance(model, ndb.Model):
            raise TypeError("%s is not a valid ndb.Model" % model)
        prop = getattr(model.__class__, name)
        if not isinstance(prop, ndb.model.Property):
            raise TypeError('%s is not a property of %s' % (name, model._class_name()))
        return prop

    def _iter_dict(self, in_dict, cv_val, remove_null_entries=False, model=None, level=None):
        '''
        Loop through the dictionary and set convert the value when needed
        '''

        if model is None:
            model = self._model

        if level is None:
            level = 0
        else:
            level += 1

        del_entries = []

        for key, value in in_dict.iteritems():
            # Skip null values
            if value is None:
                if remove_null_entries:
                    LOGGER.debug("ModelParser._iter_dict: %s queued to be deleted", key)
                    del_entries.append({"key": key, "in_dict": in_dict})
                continue

            LOGGER.debug("ModelParser._iter_dict: %s=%s (%s)[%d]", key, value, type(value), level)

            # Process the property, recursively if StructuredProperty found
            prop = self._get_property_from_model_by_name(model, key)

            # Need recurive call for StructuredProperty
            if isinstance(prop, ndb.StructuredProperty):
                if isinstance(value, dict):
                    # Get the underling model of the structured property
                    struct_model = prop._get_value(model)
                    if struct_model is None:
                        # Initialize a blank structured property is not initialized before
                        prop._set_value(model, {})
                        struct_model = prop._get_value(model)
                    self._iter_dict(value, cv_val, model=struct_model, level=level)
                else:
                    raise InvalidValueError("ndb.StructuredProperty '%s' expect a dict as value but got '%s' of type '%s'" % (prop, value, type(value)))
            else:
                # Update the entry
                try:
                    in_dict[key] = cv_val(prop, value)
                except StandardError as ex:
                    message = "Failed to run .%s converting %s for %s" % (cv_val.__name__, value, prop)
                    raise ParserConversionError(message, ex)

        # Delete null entries if needed
        if remove_null_entries:
            for entry in del_entries:
                in_dict = entry['in_dict']
                key = entry['key']
                LOGGER.debug("ModelParser._iter_dict: deleting %s", key)
                del in_dict[key]

    def value_for_property(self, prop, value):
        '''
        Convert the value for property, used when setting the model's value from a dictionary.
        Reverse of .text_from_property.  Handle the following:

        * DateProperty
        * DateTimeProperty
        * KeyProperty

        Override this method to implement custom conversion
        '''
        if value is None:
            return

        result = value
        if isinstance(prop, ndb.DateProperty):
            result = datetime.datetime.strptime(value, "%Y-%m-%d")
        elif isinstance(prop, ndb.DateTimeProperty):
            # this is equivalent of the .isoformat
            result = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
        elif isinstance(prop, ndb.KeyProperty):
            # Only attempt to convert to key if input value is a string
            if isinstance(value, basestring):
                result = self.decode_ndb_key(value)

        LOGGER.debug("ModelParser.value_for_property: prop=%s; value=%s; result=%s", prop, value, result)
        return result

    def set_dict_for_model(self, in_dict, remove_null_entries=False):
        '''
        Return dictionary object to be used for creating or updating the model.  This method create a
        shallow copy of input dictionary as not to alter the input dictionary.
        '''
        res_dict = copy.deepcopy(in_dict)
        self._iter_dict(res_dict, cv_val=self.value_for_property, remove_null_entries=remove_null_entries)
        return res_dict

    def text_from_property(self, prop, value):
        '''
        Convert the property to string value.  Reverse of .value_for_property.  Handle the following:

        * DateProperty
        * DateTimeProperty
        * KeyProperty

        Override this method to implement custom conversion
        '''
        if value is None:
            return

        result = value
        if isinstance(prop, ndb.DateProperty):
            if not isinstance(value, (datetime.date, datetime.datetime)):
                raise ValueError("Property %s expected value type of date or datetime but got '%s'" % (prop, value))
            result = value.strftime('%Y-%m-%d')
        elif isinstance(prop, ndb.DateTimeProperty):
            if not isinstance(value, (datetime.date, datetime.datetime)):
                raise ValueError("Property %s expected value type of date or datetime but got '%s'" % (prop, value))
            result = value.isoformat()
        elif isinstance(prop, ndb.KeyProperty):
            if not isinstance(value, ndb.KeyProperty):
                raise ValueError("Expected KeyProperty for %s but got '%s'" % (prop, value))
            return value.urlsafe()

        LOGGER.debug("ModelParser.text_from_property: prop=%s; value=%s; result=%s", prop, value, result)
        return result

    def get_dict_from_model(self, remove_null_entries=False):
        '''
        Format the dictionary from model.to_dict()
        '''
        in_dict = self._model.to_dict()
        self._iter_dict(in_dict, cv_val=self.text_from_property, remove_null_entries=remove_null_entries)
        return in_dict


class NdbUtilMixIn(object):
    '''
    This MixIn allow updating of entities using key.

    Class Variables

    _unique_properties:   Set the name(s) of properties that would act as unique key.  Only
                          one unique key (non primary key) per model

    _required_properties: Set the name(s) of properties that must be initialized (ie: not None). This
                          is used to override a base model that contains non required properties.

    _mode_parser_class:   NdbModelParser to use

    NOTE: this must be first parent of multiple inherentance to ensure
          that NdbUtilMixIn.__init__() is called.

    ToDo: Implement .check_unique_properties using a unique key ndb.Model
    '''

    def __init_class_variables(self):
        '''Initialize the variables that must exists for the class'''
        attrs = (
            '_unique_properties',
            '_required_properties',
            '_mode_parser_class'
        )

        for attr in attrs:
            if not hasattr(self, attr):
                setattr(self, attr, None)

        if self._mode_parser_class is None:
            self._parser = ModelParser(self)
        else:
            self._parser = self._mode_parser_class(self)

    def __init__(self, *args, **kwargs):
        # This method should only be used with ndb.Model
        if not isinstance(self, ndb.Model):
            raise NdbModelInitializationError("'%s' must be an instance of ndb.Model" % self.__class__)

        self.__init_class_variables()

        super(NdbUtilMixIn, self).__init__(*args, **kwargs)

    def __raise_dup_unique_properties(self, key):
        entry = key.get(use_cache=False)

        fields = []
        for prop_name in self._unique_properties:
            fields.append("%s=%s" % (prop_name, getattr(entry, prop_name)))
            # fields.append("%s=%s" % (prop_name, prop_name))

        raise DuplicateEntryError("Duplicated entry for %s: %s" % (self._class_name(), ','.join(fields)))

    def check_unique_properties(self, insert_mode=None):
        '''
        Check the unique constraint.  If creating a new records setting the key, needs to call this method
        with new_key populated.

        Exceptions: DuplicateEntryError
        '''
        raise NotImplementedError(".check_unique_properties is not yet implemented")

    def check_required_properties(self):
        '''
        Check and ensure that columns defined in the _required_properties are not None

        Exception: MissingRequiredPropertyError
        '''
        if self._required_properties is None:
            return

        missing_props = []
        for prop in self._required_properties:
            if getattr(self, prop) is None:
                missing_props.append(prop)
        if missing_props:
            raise MissingRequiredPropertyError(*missing_props)

    def check_parent_kind(self, *kinds):
        '''
        Used in _pre_put_hook to make sure that parent if of specific kinds passed as string.

        Exceptions: ValueError
        '''
        model_key = self.key
        if model_key:
            parent_key = model_key.parent()
            expected_kinds = set(kinds)

            if parent_key is None:
                raise ValueError("Missing parent for %s.  Expect a parent of kind(s): %s" % (model_key.kind(), ','.join(kinds)))
            elif parent_key.kind() not in expected_kinds:
                raise ValueError("%s requires a parent of kind(s) %s but got %s" % (model_key.kind(), ','.join(kinds), parent_key.kind()))

    def json_dict(self, skip_null_value=False):
        '''Return formatted dictionary to be converted to JSON'''
        return self._parser.get_dict_from_model(remove_null_entries=skip_null_value)

    @classmethod
    def __raise_if_not_same_class(cls, model, key_for_error_message=None):
        '''Raise error if model is not the class'''
        if not isinstance(model, cls):
            if key_for_error_message:
                message = "Expected model to be '%s' but key '%s' points to model '%s'" % (cls._class_name(), key_for_error_message, model.__class__.__name__)
            else:
                message = "Expected model to be '%s' but got '%s'" % (cls._class_name(), model.__class__.__name__)
            raise NdbModelMismatchError(message)

    def _patch_dict(self, data, patch):
        '''
        Update the data dictionary with content from patch
        '''
        for key in set(data.keys() + patch.keys()):
            data_entry = data.get(key)
            patch_entry = patch.get(key)

            if isinstance(data_entry, dict) or isinstance(patch_entry, dict):
                if data_entry is None:
                    data[key] = {}
                if patch_entry is None:
                    patch[key] = {}
                self._patch_dict(data[key], patch[key])
            else:
                if patch_entry is not None:
                    data[key] = patch_entry

    def update(self, in_dict, skip_null_value=False):
        '''Update model's properties from input dictionary'''
        data_dict = self._parser.set_dict_for_model(in_dict, remove_null_entries=skip_null_value)
        self.populate(**data_dict)
        return self

    def patch(self, in_dict, skip_null_value=False):
        '''Patch the model'''
        current_data = self.json_dict()
        self._patch_dict(current_data, in_dict)
        data_dict = self._parser.set_dict_for_model(current_data, remove_null_entries=skip_null_value)
        self.populate(**data_dict)
        return self

    @classmethod
    def create_from_dict(cls, in_dict, in_id=None, in_parent=None, skip_null_value=False):
        '''Create a new model from a dictionary'''
        creation_kwargs = {}

        if in_id:
            creation_kwargs["id"] = in_id

        if in_parent is not None:
            creation_kwargs["parent"] = in_parent

        model = cls(**creation_kwargs)
        return model.update(in_dict, skip_null_value=skip_null_value)

    @classmethod
    def update_from_dict(cls, in_dict, in_key, skip_null_value=False):
        '''
        Update the model of the input key with the supplied dictionary.

        Exceptions: InvalidKeyError, NdbModelMismatchError
        '''

        key = ModelParser.decode_ndb_key(in_key, raise_exception=True)
        model = key.get()
        if model is None:
            err_message = "Entry not found for key %s" % in_key
            raise InvalidKeyError(message=err_message)

        cls.__raise_if_not_same_class(model)
        return model.update(in_dict, skip_null_value=skip_null_value)

    @classmethod
    def patch_from_dict(cls, in_dict, in_key, skip_null_value=False):
        '''
        Patch the model of the input key with the supplied dictionary.

        Exceptions: InvalidKeyError, NdbModelMismatchError
        '''

        key = ModelParser.decode_ndb_key(in_key, raise_exception=True)
        model = key.get()
        if model is None:
            err_message = "Entry not found for key %s" % in_key
            raise InvalidKeyError(message=err_message)

        cls.__raise_if_not_same_class(model)
        return model.patch(in_dict, skip_null_value=skip_null_value)

    @classmethod
    def get_by_urlsafe(cls, urlsafe_key):
        '''Get an entity by key in urlsafe format.'''

        key = ModelParser.decode_ndb_key(urlsafe_key)
        if key is None:
            return None

        entry = key.get()
        if entry:
            cls.__raise_if_not_same_class(entry, urlsafe_key)
            return entry
        else:
            return None

    @classmethod
    def get_first(cls, *args, **kwargs):
        '''Return first record'''
        for entry in cls.query(*args, **kwargs):
            return entry


# ==============================================================================
# Define Stub Model -- Model that cannot be saved
#
class StubModel(NdbUtilMixIn, ndb.Model):
    '''
    Disable the put related methods
    '''
    def _put_async(self, **ctx_options):
        '''Trap async put'''
        raise PutMethodDisabledError(self.__class__)
    put_async = _put_async

    def set_from_model(self, source_model):
        '''Copy data from input source_model to stub model'''
        self._apply_model_data(self, source_model)

    def set_to_model(self, dest_model):
        '''Copy data from stub model to input source_model'''
        self._apply_model_data(dest_model, self)
        return dest_model

    @classmethod
    def _apply_model_data(cls, dest_model, source_model):
        '''Copy the data from source model to dest model only where properties name matches'''
        # ToDo: Implement recurisve json_dict() methods dealing with StructuredProperty in NdbUtilMixIn
        #       instead of the 'key' based hack below.
        for name, prop in dest_model._properties.items():
            if name == 'key' and isinstance(prop, ndb.Key):
                prop._set_value(dest_model, source_model.key)
            elif hasattr(source_model, name):
                prop._set_value(dest_model, getattr(source_model, name))
