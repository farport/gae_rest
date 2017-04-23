'''
Testing model library
'''

import unittest
import datetime

import testlib

from google.appengine.ext import ndb
from google.appengine.api.datastore_errors import BadValueError
from models import NdbUtilMixIn, MissingRequiredPropertyError # pylint: disable=E0401

READER = testlib.JsonDataReader(__file__)

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
    modified_on = ndb.DateTimeProperty()
    created_on = ndb.DateTimeProperty()

    def _pre_put_hook(self):
        self.check_required_properties()

# -------------------------------------------------------
# Define tests

class SimpleNdbNestedTest(unittest.TestCase):
    datastore_mode = "normal"

    @classmethod
    def setUpClass(cls):
        cls.shared = testlib.SharedTestData()
        cls.maxDiff = None

    def get_data(self, fname):
        '''All data for this test is under 'data/simple/' dir'''
        return READER.get('simple/%s' % fname)

    def test01_create_from_dict(self):
        '''Make sure that create_from_dict model from dict works'''
        data = self.get_data("person01.json")
        person = Person.create_from_dict(data)
        key = person.put()
        self.shared.set(key, "person01_key")

        # modified_on with value of None is expected from .json_dict
        res_dict = person.json_dict()
        self.assertIsNone(res_dict.get("modified_on"))
        del res_dict["modified_on"]

        self.assertDictEqual(res_dict, data)

    def test02_create(self):
        '''Make sure that model can still be created normally'''
        person = Person(first_name="Rosa", last_name="Eskew")
        key = person.put()
        self.shared.set(key, "person02_key")

        res_dict = person.json_dict()
        self.assertEqual(res_dict.get("first_name"), "Rosa")
        self.assertEqual(res_dict.get("last_name"), "Eskew")

    def test03_get(self):
        '''Make sure get works'''
        data = self.get_data("person01.json")
        key = self.shared.get("person01_key")
        person = key.get()
        self.assertDictEqual(person.json_dict(skip_null_value=True), data)

        expected_created_on = datetime.datetime(2017, 4, 20, 18, 56, 39, 75310)
        self.assertEqual(person.created_on, expected_created_on)

    def test04_update_from_dict(self):
        '''Make sure set_from_dict works'''
        data = self.get_data("person01_update_will.json")
        person = Person.update_from_dict(data, in_key=self.shared.get("person01_key"))
        result = person.json_dict(skip_null_value=True)
        self.assertEqual(result.get("first_name"), "Will")
        self.assertDictEqual(result, data)

    def test05_update(self):
        '''Make sure update works'''
        data = self.get_data("person01_update_betty.json")
        key = self.shared.get("person01_key")
        person = key.get()
        person.update(data)
        self.assertDictEqual(person.json_dict(skip_null_value=True), data)

    def test06_update_partial(self):
        '''
        In theory, a partial update shouldn't work as missing attributes from input
        dictionary should really set the element to None.  However, as this method
        proves, the ndb.Model.populate(...) method will simply skip the missing
        elements.

        Leaving this "partial update" as a "feature"
        '''
        data = self.get_data("person02.json")
        result = data.copy()

        data.delete("first_name")
        data.delete("last_name")
        person = Person.update_from_dict(data, in_key=self.shared.get("person02_key"))
        person.put()

        self.assertDictEqual(person.json_dict(skip_null_value=True), result)

    def test07_patch_from_dict(self):
        '''Partial update should be done using the .patch_from_dict method'''
        data = self.get_data("person02_patch_jerry.json")
        result = self.get_data("person02_patch_jerry_check.json")

        key = self.shared.get("person02_key")
        person = Person.patch_from_dict(data, in_key=key)
        person.put()

        self.assertDictEqual(person.json_dict(skip_null_value=True), result)

    def test08_path(self):
        '''Partial update should be done using the .patch method'''
        data = self.get_data("person01_patch_sara.json")
        result = self.get_data("person01_patch_sara_check.json")

        key = self.shared.get("person01_key")
        person = key.get()
        person.patch(data)
        person.put()

        self.assertDictEqual(person.json_dict(skip_null_value=True), result)

    def test10_required_error(self):
        '''Test required property'''
        Person._required_properties = ('modified_on', ) # pylint: disable=W0212

        data = self.get_data("person01.json")
        person = Person.create_from_dict(data)

        self.assertRaises(MissingRequiredPropertyError, person.put)
        self.assertRaises(BadValueError, person.put)

if __name__ == '__main__':
    testlib.TestRunner.run(SimpleNdbNestedTest, verbosity=2, failfast=True)
