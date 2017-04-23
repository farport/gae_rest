'''
Testing ModelParser for NdbModelMixIn
'''

import unittest
import datetime
import time

import testlib

from google.appengine.ext import ndb
from models import NdbModelMixIn, ModelParser, ParserConversionError # pylint: disable=E0401

READER = testlib.JsonDataReader(__file__)

# -------------------------------------------------------
# Define basic model.
class DateParser(ModelParser):
    '''
    Simple Model Parse that convert the datetime to integer
    '''
    def value_for_property(self, prop, value):
        '''Expect input datetime value to be an integer'''
        if value is None:
            return

        result = value
        if isinstance(prop, ndb.DateTimeProperty) and not isinstance(prop, ndb.DateProperty):
            result = datetime.datetime.fromtimestamp(value)
        else:
            result = super(DateParser, self).value_for_property(prop, value)

        return result

    def text_from_property(self, prop, value):
        '''Output integer for datetime value'''
        if value is None:
            return

        result = value
        if isinstance(prop, ndb.DateTimeProperty) and not isinstance(prop, ndb.DateProperty):
            result = time.mktime(value.timetuple())
        else:
            result = super(DateParser, self).text_from_property(prop, value)

        return result


class Person(NdbModelMixIn, ndb.Model):
    _mode_parser_class = DateParser

    name = ndb.StringProperty()
    birthday = ndb.DateProperty()
    created_on = ndb.DateTimeProperty()


# -------------------------------------------------------
# Define tests

class ModelParserTest(unittest.TestCase):
    datastore_mode = "normal"

    @classmethod
    def setUpClass(cls):
        cls.shared = testlib.SharedTestData()
        # timestamp of 1492950082 in datetime:
        cls.create_dt = datetime.datetime(2017, 4, 23, 14, 21, 22)
        cls.birth_dt = datetime.date(1990, 1, 19)
        cls.maxDiff = None

    def get_data(self, fname):
        '''All data for this test is under 'data/simple/' dir'''
        return READER.get('parser/%s' % fname)

    def test01_create(self):
        '''Make sure models is created correctly'''
        data = self.get_data("person.json")
        person = Person.create_from_dict(data)
        self.shared.set(person.put(), "person_key")

        self.assertEqual(person.birthday, self.birth_dt)
        self.assertEqual(person.created_on, self.create_dt)

    def test02_get(self):
        '''Make sure that get will return expected dictionary'''
        data = self.get_data("person.json")
        key = self.shared.get("person_key")
        person = key.get()

        self.assertEqual(person.birthday, self.birth_dt)
        self.assertEqual(person.created_on, self.create_dt)

        self.assertDictEqual(person.json_dict(), data)

    def test04_create_null(self):
        '''Make sure null data are handled correctly'''
        data = self.get_data("person_null.json")
        result = {"name": "NULL Person"}
        person = Person.create_from_dict(data)
        person.put()

        self.assertEqual(person.name, result["name"])
        self.assertIsNone(person.birthday)
        self.assertIsNone(person.created_on)

        self.assertDictEqual(person.json_dict(), data)
        # Make sure skip null works
        self.assertDictEqual(person.json_dict(skip_null_value=True), result)

    def test05_create_error(self):
        '''Check conversion error handler'''
        data = self.get_data("person_error.json")
        self.assertRaises(ParserConversionError, Person.create_from_dict, data)


if __name__ == '__main__':
    # TestRunner is needed here as it will setup the datastore
    testlib.TestRunner.run(ModelParserTest, verbosity=2, failfast=True)



