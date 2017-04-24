'''
Testing NdbViewMixIn
'''

import unittest
import datetime
import time

import testlib

from google.appengine.ext import ndb
from models import NdbModelMixIn, ModelParser, NdbModelMismatchError # pylint: disable=E0401
from views import NdbViewMixIn # pylint: disable=E0401

READER = testlib.JsonDataReader(__file__)

# -------------------------------------------------------
# Define basic model.
class PersonView(NdbModelMixIn, NdbViewMixIn, ndb.Model):
    _identity_property = "idperson"
    _classname_property = "type"
    _parent_property = "parent_key"

    name = ndb.StringProperty()
    balance = ndb.FloatProperty()
    created_on = ndb.DateTimeProperty()


# -------------------------------------------------------
# Define tests
class ViewTest(unittest.TestCase):
    datastore_mode = "normal"

    @classmethod
    def setUpClass(cls):
        testlib.SharedTestData.unload()
        cls.shared = testlib.SharedTestData()
        cls.maxDiff = None

    def get_data(self, fname): # pylint: disable=C0111
        return READER.get('view/%s' % fname)

    def test01_create(self):
        '''Make sure that model can be created'''
        data = self.get_data("person01.json")
        person = PersonView.view_create(data)
        urlsafe_key = person["key"]
        key = ndb.Key(urlsafe=urlsafe_key)
        self.shared.set(key, "person01_key")

        result = self.get_data("person01_view.json")
        result["idperson"] = key.id()
        result["key"] = urlsafe_key

        self.assertDictEqual(person, result)

    def test02_view_get(self):
        '''Make sure that .view_get returns the right values'''
        result = self.get_data("person01_view.json")
        key = self.shared.get("person01_key")
        person = PersonView.view_get(key.urlsafe())

        result["idperson"] = key.id()
        result["key"] = key.urlsafe()

        self.assertDictEqual(person, result)
        self.shared.set(person, "person01_result")

    def test03_view_create_parsed(self):
        '''Make sure that view._read_dict_attributes works'''
        data_dict = self.shared.get("person01_result")
        parsed = PersonView._read_dict_attributes(data_dict.copy()) # pylint: disable=W0212

        self.assertEqual(parsed["key"], data_dict.get("key"))
        self.assertEqual(parsed["id"], data_dict.get("idperson"))
        self.assertEqual(parsed["parent"], data_dict.get("parent_key"))
        self.assertEqual(parsed["classname"], data_dict.get("type"))

    def test04_view_update(self):
        '''Make sure update works'''
        data = self.get_data("person01_update.json")
        key = self.shared.get("person01_key")
        data["key"] = key.urlsafe()

        # Create expected result from data
        result = data.copy()
        result["idperson"] = key.id()
        result["parent_key"] = None
        result["type"] = "PersonView"

        person = PersonView.view_update(data)
        self.assertDictEqual(person, result)
        self.shared.set(person, "person01_result")

    def test05_view_create_id_parent(self):
        '''Create a person with parent'''
        data = self.get_data("person02.json")
        parent_key = self.shared.get("person01_key")
        data["parent_key"] = parent_key.urlsafe()
        result = data.copy()

        person = PersonView.view_create(data)
        urlsafe_key = person["key"]
        key = ndb.Key(urlsafe=urlsafe_key)
        self.shared.set(key, "person02_key")

        result["key"] = urlsafe_key
        self.assertDictEqual(person, result)
        self.shared.set(person, "person02_result")

    def test06_view_create(self):
        '''Create 3rd person'''
        data = self.get_data("person03.json")
        person = PersonView.view_create(data)

        urlsafe_key = person["key"]
        key = ndb.Key(urlsafe=urlsafe_key)
        self.shared.set(key, "person03_key")

        self.assertIsNone(person.get('name'))

    def test07_view_patch(self):
        '''Make sure view_patch works'''
        data = self.get_data("person03_patch.json")
        key = self.shared.get("person03_key")
        data["key"] = key.urlsafe()

        # Prepare result
        result = self.get_data("person03.json")
        result["idperson"] = key.id()
        result["name"] = data["name"]
        result["key"] = data["key"]
        result["type"] = "PersonView"
        result["parent_key"] = None

        person = PersonView.view_patch(data)
        self.assertDictEqual(person, result)
        self.shared.set(person, "person03_result")

    def test08_view_create_error(self):
        '''Make sure that wrong _classname_property setting raise exception'''
        data = self.get_data("person01.json")
        data["type"] = "Person"
        self.assertRaises(NdbModelMismatchError, PersonView.view_create, data)

    def test10_view_query(self):
        '''Make sure query works'''
        result = {}
        for entry in ('person01', 'person02', 'person03'):
            key = self.shared.get("%s_key" % entry)
            result[key.urlsafe()] = self.shared.get("%s_result" % entry)

        data = {}
        tcount = 0
        for entry in PersonView.view_query():
            data[entry['key']] = entry
            tcount += 1

        self.assertEqual(tcount, 3)
        self.assertDictEqual(data, result)

    def test11_view_query_parent(self):
        '''Make sure query by parent works'''
        parent_key = self.shared.get("person01_key").urlsafe()
        result = {}
        for entry in ('person02', ):
            key = self.shared.get("%s_key" % entry)
            result[key.urlsafe()] = self.shared.get("%s_result" % entry)

        data = {}
        tcount = 0
        for entry in PersonView.view_query(in_parent=parent_key):
            # Skip itself
            if entry['key'] == parent_key:
                continue
            data[entry['key']] = entry
            tcount += 1

        self.assertEqual(tcount, 1)
        self.assertDictEqual(data, result)

    def test12_view_delete(self):
        '''Make sure view_delete works'''
        key = self.shared.get("person01_key")
        urlsafe_key = key.urlsafe()
        self.assertIsNotNone(key.get())

        PersonView.view_delete(urlsafe_key)
        self.assertIsNone(key.get())

        tcount = 0
        for _ in PersonView.view_query():
            tcount += 1
        self.assertEqual(tcount, 2)



if __name__ == '__main__':
    # TestRunner is needed here as it will setup the datastore
    testlib.TestRunner.run(ViewTest, verbosity=2, failfast=True)
