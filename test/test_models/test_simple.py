'''
Testing model library
'''

import unittest
import testlib

from google.appengine.ext import ndb
from models import NdbUtilMixIn

import pprint


# -------------------------------------------------------
# Define basic model.  Testing a deep nesting model
class Country(ndb.Model):
    code = ndb.StringProperty()
    country = ndb.StringProperty()
    residence_since = ndb.DateProperty()

class CityCountry(ndb.Model):
    city = ndb.StringProperty()
    region = ndb.StringProperty()
    post_code = ndb.StringProperty()
    country = ndb.StructuredProperty(Country)

class Address(ndb.Model):
    lines = ndb.StringProperty(repeated=True)
    city_country = ndb.StructuredProperty(CityCountry)

class Person(NdbUtilMixIn, ndb.Model):
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    age = ndb.IntegerProperty()
    balance = ndb.FloatProperty()
    address = ndb.StructuredProperty(Address)
    created_on = ndb.DateTimeProperty()

# "created_on": "2017-04-19T22:04:09"

# -------------------------------------------------------
# Define tests
reader = testlib.JsonDataReader(__file__)

class TestConfigurationStore(unittest.TestCase):
    datastore_mode = "normal"

    def test01_create(self):
        data = reader.get('person01.json')
        person = Person.create_from_dict(data)
        key = person.put()

        res_dict = person.json_dict()

        self.assertEqual(data.created_on, res_dict.get("created_on"))
        self.assertEqual(res_dict, data)


if __name__ == '__main__':
    testlib.TestRunner.run(TestConfigurationStore, verbosity=2, failfast=True)
