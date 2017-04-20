from __future__ import print_function

import copy
import datetime

from google.appengine.ext import ndb

from google.net.proto.ProtocolBuffer import ProtocolBufferDecodeError
from google.appengine.api.datastore_errors import Error, BadValueError

from core import ConfigurationStore

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
    pass

class UnAuthorizedException(NdbModelError):
    pass

class DuplicateEntryError(NdbModelError):
    pass

class InvalidValueError(NdbModelError, BadValueError):
    pass

class UninitializedRequiredPropertyError(InvalidValueError):
    def __init__(self, *prop_names):
        if len(prop_names) == 1:
            message = "Required property '%s' is not initialized." % prop_names
        elif len(prop_names) > 1:
            message = "Required properties '%s' are not initialized." % ",".join(["'%s'" % x for x in prop_names])
        else:
            raise NdbModelError("UninitializedRequiredPropertyError error received no property name")
        super(UninitializedRequiredPropertyError, self).__init__(message)


class PutMethodDisabledError(NdbModelError):
    def __init__(self, object_classname, alternative_put_method_name='.save'):
        message = "%s object must be persisted using the %s method" % (object_classname, alternative_put_method_name)
        super(PutMethodDisabledError, self).__init__(message)



# ==============================================================================
# ndb.Model related
#
class ModelParser(object):
    '''
    Class Variables

    _identity_property:   Set the name of property that should be set as ID of the model.
                          Support a single property only so no composite key.

    _parent_property:     When returning identity_property, generate assoicated parent key

    _key_property:        Attribute name for urlsafe version of key

    _classname_property:  Return the name of the class in the given attribute

    _skip_update_columns: Columns that shouldn't be updated by create/update_from_dict
    '''

    _identity_property = None
    _parent_property = None
    _key_property = None
    _classname_property = None
    _skip_update_columns = set([])

    def __init__(self, model):
        self._model = model

    def _get_property_from_model_by_name(self, model, name):
        if not isinstance(model, ndb.Model):
            raise TypeError("%s is not a valid ndb.Model" % model)
        prop = getattr(model.__class__, name)
        if not isinstance(prop, ndb.model.Property):
            raise TypeError('%s is not a property of %s' % (name, model._class_name()))
        return prop

    def _iter_dict(self, in_dict, cv_val, model=None, skip_null_value=False, level=None):
        '''
        Loop through the dictionary and set convert the value when needed
        '''

        if model is None:
            model = self._model

        if level is None:
            level = 0
        else:
            level += 1

        for key, value in in_dict.iteritems():
            # Skip null values
            if skip_null_value and value is None:
                continue

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
                # Update the entry
                in_dict[key] = cv_val(prop, value)

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
            # result = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
            result = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
        elif isinstance(prop, ndb.KeyProperty):
            # Only attempt to convert to key if input value is a string
            if isinstance(value, basestring):
                # Fix per: https://github.com/googlecloudplatform/datastore-ndb-python/issues/143
                try:
                    result = ndb.Key(urlsafe=value)
                except ProtocolBufferDecodeError:
                    pass
                except StandardError as e:
                    if e.__class__.__name__ == 'ProtocolBufferDecodeError':
                        pass
                    else:
                        raise e
        return result

    def dict_for_model(self, in_dict, skip_null_value=False):
        '''
        Return dictionary object to be used for the model.  This method create a shallow copy of
        input dictionary as not to alter the input dictionary.
        '''
        res_dict = copy.deepcopy(in_dict)
        self._iter_dict(res_dict, cv_val=self.value_for_property, skip_null_value=skip_null_value)
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
            # result = value.strftime('%Y-%m-%d')
        elif isinstance(prop, ndb.KeyProperty):
            if not isinstance(value, ndb.KeyProperty):
                raise ValueError("Expected KeyProperty for %s but got '%s'" % (prop, value))
            return value.urlsafe()
        # print("### text_from_property: %s=%s [type: %s]" % (prop, result, type(result)))

        return result

    def dict_from_model(self, skip_null_value=False):
        in_dict = self._model.to_dict()
        self._iter_dict(in_dict, cv_val=self.text_from_property, skip_null_value=skip_null_value)
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

    def __check_if_property_exists(self, properties):
        '''
        Check if properties passed indeed exists.  Used during init
        '''
        if properties is None:
            return

        if isinstance(properties, basestring):
            if properties not in self._properties:
                raise NdbModelInitializationError("%s is not a valid property in %s" % (properties, self._class_name()))
        else:
            for prop_name in properties:
                if prop_name not in self._properties:
                    raise NdbModelInitializationError("%s is not a valid property in %s" % (prop_name, self._class_name()))

    def __init__(self, *args, **kwargs):
        # This method should only be used with ndb.Model
        if not isinstance(self, ndb.Model):
            raise NdbModelInitializationError("'%s' must be an instance of ndb.Model" % self.__class__)

        self.__init_class_variables()

        super(NdbUtilMixIn, self).__init__(*args, **kwargs)

    def __update_model(self, in_dict, insert_mode=False, skip_null_value=False):
        '''Wrapper around .populate removing columns that shouldn't be updated'''
        self.populate(**in_dict)
        return self

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
        if self._unique_properties is None:
            return

        # Generate query object searching for existing records from datastore
        model = self.__class__
        search_args = []
        for col in self._unique_properties:
            model_prop = getattr(model, col)
            self_prop = getattr(self, col)
            search_args.append(model_prop == self_prop)
        qry = self.query(*search_args)

        # Check if insert or update
        if insert_mode is None:
            insert_mode = self.key is None

        # Check if entries exists, avoid using cache
        for key in qry.iter(keys_only=True):
            if insert_mode:
                # If adding
                self.__raise_dup_unique_properties(key)
            else:
                # If update
                if key == self.key:
                    continue
                else:
                    self.__raise_dup_unique_properties(key)

    def check_required_properties(self):
        '''
        Check and ensure that columns defined in the _required_properties are not None
        '''
        if self._required_properties is None:
            return

        missing_props = []
        for prop in self._required_properties:
            if getattr(self, prop) is None:
                missing_props.append(prop)
        if missing_props:
            raise UninitializedRequiredPropertyError(*missing_props)

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

    def set_from_dict(self, in_dict, skip_null_value=False):
        return self.__update_model(in_dict, insert_mode=False, skip_null_value=skip_null_value)

    def json_dict(self, skip_null_value=False):
        return self._parser.dict_from_model(skip_null_value)

    @classmethod
    def __raise_if_not_same_class(cls, model, in_key=None):
        '''Raise error if model is not the class'''
        if not isinstance(model, cls):
            if in_key:
                message = "Expected model to be '%s' but key '%s' points to model '%s'" % (cls._class_name(), in_key, model.__class__.__name__)
            else:
                message = "Expected model to be '%s' but got '%s'" % (cls._class_name(), model.__class__.__name__)
            raise NdbModelMismatchError(message)

    @classmethod
    def create_from_dict(cls, in_dict, parent=None, skip_null_value=False):
        '''
        Factory method to create a new model from a dictionary

        # ToDo: add validation for given input from _classname_property if defined.
        '''

        key_defined = hasattr(cls, '_key_property') and cls._key_property is not None
        id_defined = hasattr(cls, '_identity_property') and cls._identity_property is not None
        parent_defined = hasattr(cls, '_parent_property') and cls._parent_property is not None

        if key_defined and cls._key_property in in_dict:
            raise NdbModelError("'%s' key entry is not expected in the .create_from_dict method" % cls._key_property)

        creation_kwargs = {}

        if id_defined and cls._identity_property in in_dict:
            creation_kwargs["id"] = in_dict.get(cls._identity_property)

        # If parent param used, use that instead of the ._parent_property defined
        if parent is not None:
            creation_kwargs["parent"] = parent
        elif parent_defined and cls._parent_property in in_dict:
            creation_kwargs["parent"] = in_dict.get(cls._parent_property)

        model = cls(**creation_kwargs)
        in_dict = model._parser.dict_for_model(in_dict, skip_null_value=skip_null_value)

        return model.__update_model(in_dict, skip_null_value=skip_null_value)

    @classmethod
    def __translate_key(cls, in_key):
        if in_key is None:
            return None
        elif isinstance(in_key, ndb.Key):
            res = in_key
        else:
            res = ndb.Key(urlsafe=in_key)
        return res

    @classmethod
    def update_from_dict(cls, in_dict, parent=None, skip_null_value=False):
        '''
        Update an existing model from a dictionary.  A unique identifier must be provided
        and can be either a key or an ID.

        Please note that for entity with ancestor, use key or set the parent property.
        '''

        key_defined = hasattr(cls, '_key_property') and cls._key_property is not None
        id_defined = hasattr(cls, '_identity_property') and cls._identity_property is not None
        parent_defined = hasattr(cls, '_parent_property') and cls._parent_property is not None

        if key_defined and cls._key_property in in_dict:
            key_provided = in_dict.get(cls._key_property)
            id_provided = None
        elif id_defined and cls._identity_property in in_dict:
            key_provided = None
            id_provided = in_dict.get(cls._identity_property)
        else:
            if key_defined or key_defined:
                attrs = []

                if key_defined:
                    attrs.append("'%s'" % cls._key_property)
                if id_defined:
                    attrs.append("'%s'" % cls._identity_property)

                if len(attrs) == 1:
                    cols_name = attrs[0]
                else:
                    cols_name = ", ".join(attrs)

                raise NdbModelError("%s identifier(s) expected in the .update_from_dict method" % cols_name)
            else:
                raise NdbModelError("Either _key_property or _identity_property needs to be defined in order to use .update_from_dict method")

        if id_provided is not None:
            # Parent is only relevant when ID is provided instead of key
            if parent is not None:
                parent_provided = parent
            elif parent_defined and cls._parent_property in in_dict:
                parent_provided = in_dict.get(cls._parent_property)
            else:
                parent_provided = None
            key = ndb.Key(cls, id_provided, parent=cls.__translate_key(parent_provided))
        elif key_provided is not None:
            key = cls.__translate_key(key_provided)

        model = key.get()
        if model is None:
            raise NdbModelError("Entry not found for key %s" % key_provided)

        cls.__raise_if_not_same_class(model, key_provided)

        return model.__update_model(in_dict, insert_mode=False, skip_null_value=skip_null_value)

    @classmethod
    def get_by_urlsafe(cls, urlsafe_id):
        '''Get an entity by key in urlsafe format.'''
        try:
            key = ndb.Key(urlsafe=urlsafe_id)
        except Exception, e:
            if e.__class__.__name__ == 'ProtocolBufferDecodeError':
                return None
            else:
                raise

        entry = key.get()
        if entry:
            cls.__raise_if_not_same_class(entry, urlsafe_id)
            return entry
        else:
            return None

    @classmethod
    def get_first(cls, *args, **kwargs):
        '''Return first record'''
        for entry in cls.query(*args, **kwargs):
            return entry

