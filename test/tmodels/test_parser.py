'''
Testing ModelParser for NdbUtilMixIn
'''

import unittest
import datetime
import time

import testlib

from google.appengine.ext import ndb
from models import NdbUtilMixIn, ModelParser # pylint: disable=E0401

READER = testlib.JsonDataReader(__file__)

# -------------------------------------------------------
# Define basic model.  Testing a deep nesting model
class DateParser(ModelParser):
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


class Person(NdbUtilMixIn, ndb.Model):
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
        cls.create_dt = datetime.datetime(2017, 4, 23, 14, 21, 22)
        cls.birth_dt = datetime.date(1990, 1, 19)
        cls.maxDiff = None

    def get_data(self, fname):
        '''All data for this test is under 'data/simple/' dir'''
        return READER.get('parser/%s' % fname)

    def test01_create(self):
        '''Make sure create works'''
        data = self.get_data("person.json")
        person = Person.create_from_dict(data)
        self.shared.set(person.put(), "person_key")

        self.assertEqual(person.birthday, self.birth_dt)
        self.assertEqual(person.created_on, self.create_dt)

    def test02_get(self):
        '''Make sure that get works'''
        data = self.get_data("person.json")
        key = self.shared.get("person_key")
        person = key.get()

        self.assertEqual(person.birthday, self.birth_dt)
        self.assertEqual(person.created_on, self.create_dt)

        self.assertDictEqual(person.json_dict(), data)


if __name__ == '__main__':
    # TestRunner is needed here as it will setup the datastore
    testlib.TestRunner.run(ModelParserTest, verbosity=2, failfast=True)



