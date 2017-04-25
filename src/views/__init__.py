'''
View utitiles

by: marcos.lin@farport.co
on: 23 April 2017

View scenarios

Model -> View -> RestActions
'''
# pylint: disable=W0212

import json
from google.appengine.ext import ndb

from core import ConfigurationStore, scream_print
from models import NdbModelError, NdbModelMismatchError
with ConfigurationStore() as c:
    LOGGER = c.logger


# ==============================================================================
# Define Exceptions
#
class NdbViewError(NdbModelError):
    '''Generic and base view error'''
    pass

class ViewValueError(NdbViewError):
    '''Value Error for View'''
    pass

class KeyMisMatchViewError(NdbViewError):
    '''Key from url does not match from key property found in dictionary'''
    def __init__(self, json_key, url_key):
        message = "Key provided in the JSON '%s' does not match the one URL '%s'" % (json_key, url_key)
        super(KeyMisMatchViewError, self).__init__(message)


# ==============================================================================
# View Parser
#
class NdbViewParser(object):

    class _Encoder(json.JSONEncoder):
        pass

    class _Decoder(json.JSONDecoder):
        pass

    @classmethod
    def encoder(cls):
        return NdbViewParser._Encoder

    @classmethod
    def decoder(cls):
        return NdbViewParser._Decoder

# ==============================================================================
# Define View
#
class NdbViewMixIn(object):
    '''
    A view object allow updating of entities using key.  Class Variables:

    _identity_property:   Set the name of property that should be set as ID of the model.
                          Support a single property only so no composite key.

    _parent_property:     When returning identity_property, generate assoicated parent key

    _key_property:        Return and parse the input as model's KEY using the attribute name provided
                          Defaults to 'key'

    _classname_property:  Return the name of the class in the given attribute

    _skip_update_columns: Columns that shouldn't be updated by create/update_from_dict
    '''

    # Mapping of the supported attributes to internal result dictionary
    ATTRIBUTE_RESULT_MAP = {
        '_identity_property': 'id',
        '_parent_property': 'parent',
        '_key_property': 'key',
        '_classname_property': 'classname'
    }

    @classmethod
    def __init_class_variables(cls):
        '''Initialize the variables that must exists for the class'''
        if not hasattr(cls, '_initialized'):
            attrs = cls.ATTRIBUTE_RESULT_MAP.keys()
            attrs.append('_skip_update_columns')

            for attr in attrs:
                if not hasattr(cls, attr):
                    # Key property is required
                    if attr == '_key_property':
                        setattr(cls, attr, "key")
                    else:
                        setattr(cls, attr, None)
            setattr(cls, '_initialized', True)

    @classmethod
    def _read_dict_attributes(cls, in_dict):
        '''
        Parse the input dictionary for the defined attributes used by methods that is designed
        to update the model.

        Note: will modify incoming dictionary
        '''
        result = {}

        for attr, reskey in cls.ATTRIBUTE_RESULT_MAP.iteritems():
            attr_value = getattr(cls, attr)
            LOGGER.debug("%s._read_dict_attributes checking attribute: %s=%s", cls.__name__, attr, attr_value)
            if attr_value and attr_value in in_dict:
                # Make sure that classname is used correctly
                if attr == "_classname_property":
                    if in_dict[attr_value] != cls.__name__:
                        raise NdbModelMismatchError("Expected '%s' but got '%s' for '%s' property" % (cls.__name__, in_dict[attr_value], attr_value))

                result[reskey] = in_dict[attr_value]
                del in_dict[attr_value]

        LOGGER.debug("%s._read_dict_attributes result keys: %s", cls.__name__, result.keys())
        return result

    @classmethod
    def _set_dict_attributes(cls, model):
        data_dict = model.json_dict()
        for attr in cls.ATTRIBUTE_RESULT_MAP:
            attr_value = getattr(cls, attr)
            if attr_value:
                if attr == '_identity_property':
                    data_dict[attr_value] = model.key.id()
                elif attr == '_parent_property':
                    parent = model.key.parent()
                    if parent:
                        data_dict[attr_value] = parent.urlsafe()
                    else:
                        data_dict[attr_value] = None
                elif attr == '_key_property':
                    data_dict[attr_value] = model.key.urlsafe()
                elif attr == '_classname_property':
                    data_dict[attr_value] = model.__class__.__name__
        return data_dict

    @classmethod
    def view_query(cls, *args, **kwargs):
        '''
        Return a generator of items, accepting a `in_parent` which is urlsafe key

        Exceptions: InvalidKeyError
        '''
        cls.__init_class_variables()

        # Convert urlsafe from in_parent to ndb.Key for ancestor
        if 'in_parent' in kwargs:
            parent = cls.get_key_by_urlsafe(kwargs['in_parent'], raise_exception=True)
            del kwargs['in_parent']
            kwargs['ancestor'] = parent

        # Query the data store
        for model in cls.query(*args, **kwargs):
            yield cls._set_dict_attributes(model)

    @classmethod
    def view_get(cls, urlsafe_key):
        '''
        Get a dictionary for the given string based key

        Exceptions: InvalidKeyError, NdbModelMismatchError
        '''
        LOGGER.debug("%s.get called with key '%s'", cls.__name__, urlsafe_key)
        cls.__init_class_variables()
        model = cls.get_by_urlsafe(urlsafe_key)
        if model:
            return cls._set_dict_attributes(model)

    @classmethod
    def view_delete(cls, urlsafe_key):
        '''
        Delete the entry

        Exceptions: InvalidKeyError
        '''
        key = cls.get_key_by_urlsafe(urlsafe_key, raise_exception=True)
        key.delete()

    @classmethod
    def view_create(cls, in_dict, skip_null_value=False):
        '''
        Create an entry and return dictionary
        NOTE: Incoming dictionary will be modified

        Exceptions: NdbViewError, InvalidKeyError, NdbModelMismatchError
        '''
        cls.__init_class_variables()
        parsed = cls._read_dict_attributes(in_dict)

        # key property is not allowed on created.  If not trapped, it would simply be ignored
        if 'key' in parsed:
            raise ViewValueError("'%s' key entry is not expected in the .view_create method" % parsed['key'])

        model = cls.create_from_dict(in_dict, in_id=parsed.get('id'), in_parent=parsed.get('parent'), skip_null_value=skip_null_value)
        model.put()
        return cls._set_dict_attributes(model)

    @classmethod
    def _validate_input_urlsafe_key(self, key_property, in_key):
        '''
        Used by methods that could pass both the urlsafe_key and key property

        Exception: ViewValueError, KeyMisMatchViewError
        '''
        if key_property is None and in_key is None:
            raise ViewValueError("Key property or urlsafe_key is required for this operation.")

        if key_property is None:
            result = in_key
        elif in_key is None:
            result = key_property
        else:
            if in_key == key_property:
                result = in_key
            else:
                raise KeyMisMatchViewError(key_property, in_key)

        return result

    @classmethod
    def view_update(cls, in_dict, in_key=None, skip_null_value=False):
        '''
        Update the incoming in_dict
        NOTE: Incoming dictionary will be modified

        Exception: ViewValueError, KeyMisMatchViewError
        '''
        cls.__init_class_variables()
        parsed = cls._read_dict_attributes(in_dict)
        key = cls._validate_input_urlsafe_key(parsed.get('key'), in_key)
        model = cls.update_from_dict(in_dict, in_key=key, skip_null_value=skip_null_value)
        if model:
            model.put()
            return cls._set_dict_attributes(model)

    @classmethod
    def view_patch(cls, in_dict, in_key=None, skip_null_value=False):
        '''
        Patch the incoming in_dict
        NOTE: Incoming dictionary will be modified

        Exception: ViewValueError, KeyMisMatchViewError
        '''
        cls.__init_class_variables()
        parsed = cls._read_dict_attributes(in_dict)
        key = cls._validate_input_urlsafe_key(parsed.get('key'), in_key)
        model = cls.patch_from_dict(in_dict, in_key=key, skip_null_value=skip_null_value)
        if model:
            model.put()
            return cls._set_dict_attributes(model)
