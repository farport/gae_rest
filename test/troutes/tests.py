'''
Testing router library
'''

import os
import unittest
from flask import Flask, Blueprint

import testlib

from google.appengine.ext import ndb
from models import NdbModelMixIn # pylint: disable=E0401
from views import NdbViewMixIn # pylint: disable=E0401
from routes import RESTRouteGenerator # pylint: disable=E0401

READER = testlib.JsonDataReader(__file__)

# -------------------------------------------------------
# Define models
class RPerson(NdbModelMixIn, NdbViewMixIn, ndb.Model):
    _identity_property = "idperson"

    name = ndb.StringProperty()
    balance = ndb.FloatProperty()
    created_on = ndb.DateTimeProperty()

class RStore(NdbModelMixIn, NdbViewMixIn, ndb.Model):
    _identity_property = "idstore"
    _key_property = "ref"

    name = ndb.StringProperty()
    city = ndb.StringProperty()


# -------------------------------------------------------
# Define tests
class BaseRouteTest(unittest.TestCase):
    datastore_mode = "normal"
    shared = None
    app = None
    base_url = ""

    def get_data(self, fname): # pylint: disable=C0111
        return READER.get(fname)

    def get_url(self, url):
        '''Return in reference to base_url'''
        return "%s%s" % (self.base_url, url)

    def strip_spaces(self, in_text):
        '''Trim white space from lines'''
        result = []
        for line in in_text.split(os.linesep):
            result.append(line.strip())
        return "".join(result)

    def assertJsonTextEqual(self, in_str1, in_str2): # pylint: disable=C0103
        '''A simple wrapper to trim multi line string before comparison'''
        str1 = self.strip_spaces(in_str1)
        str2 = self.strip_spaces(in_str2)
        self.assertEqual(str1, str2)

    def post(self, in_url, in_easy_dict, check_response=True):
        '''Simple POST wrapper for test_client'''
        url = self.get_url(in_url)
        with self.app.test_client() as tclient:
            resp = tclient.post(url, data=in_easy_dict.json_text(), content_type='application/json')

        if check_response:
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.content_type, "application/json")

        return resp

    def get(self, in_url, check_response=True):
        '''Simple GET wrapper for test_client'''
        url = self.get_url(in_url)
        with self.app.test_client() as tclient:
            resp = tclient.get(url)

        if check_response:
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.content_type, "application/json")

        return resp

    def delete(self, in_url, check_response=True):
        '''Simple GET wrapper for test_client'''
        url = self.get_url(in_url)
        with self.app.test_client() as tclient:
            resp = tclient.delete(url)

        if check_response:
            self.assertEqual(resp.status_code, 200)

        return resp

    def put(self, in_url, in_easy_dict, check_response=True):
        '''Simple PUT wrapper for test_client'''
        url = self.get_url(in_url)
        with self.app.test_client() as tclient:
            resp = tclient.put(url, data=in_easy_dict.json_text(), content_type='application/json')

        if check_response:
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.content_type, "application/json")

        return resp

    def test01_person_create(self):
        '''Test POST for RPerson creation'''
        data = self.get_data("person01.json")
        result = self.get_data("person01_result.txt")
        resp = self.post("/rperson/", data)
        resp_text = resp.get_data()

        # Parse resp_text to get the key
        res_json = READER.parse(resp_text)
        self.assertIsNotNone(res_json.get('key'))
        self.shared.set(res_json.get('key'), "person01_key")
        self.shared.set(resp_text, "person01_resp")

        # Make sure result is as expected
        self.assertJsonTextEqual(resp_text, result)

    def test02_person_get(self):
        '''Test GET for RPerson created'''
        result = self.shared.get("person01_resp")
        key = self.shared.get('person01_key')
        resp = self.get("/rperson/%s" % key)
        self.assertMultiLineEqual(resp.get_data(), result)

    def test03_person_create(self):
        '''Test POST for Second RPerson creation'''
        data = self.get_data("person02.json")
        resp = self.post("/rperson/", data)
        resp_text = resp.get_data()

        # Parse resp_text to get the key
        res_json = READER.parse(resp_text)
        self.assertIsNotNone(res_json.get('key'))
        self.shared.set(res_json.get('key'), "person02_key")

        # Check that DB has been updated
        person = RPerson.get_by_urlsafe(res_json.get('key'))
        self.assertIsNotNone(person)
        self.assertEqual(person.name, "Jerry Martin")

    def test04_person_put(self):
        '''Test PUT for RPerson'''
        data = self.get_data("person02_update.json")
        key = self.shared.get('person02_key')
        resp = self.put("/rperson/%s" % key, data)
        resp_text = resp.get_data()

        # Parse resp_text and check for key and updated name
        res_json = READER.parse(resp_text)
        self.assertEqual(res_json.get('key'), key)
        self.assertEqual(res_json.get('name'), "Steve Martin")
        self.shared.set(resp_text, "person02_resp")

        # Check that DB has been updated
        person = RPerson.get_by_urlsafe(key)
        self.assertIsNotNone(person)
        self.assertEqual(person.name, "Steve Martin")


    def test10_store_create(self):
        '''Test POST for RStore creation'''
        data = self.get_data("store01.json")
        result = self.get_data("store01_result.txt")
        resp = self.post("/rstore/", data)
        resp_text = resp.get_data()

        # Parse resp_text to get the key
        res_json = READER.parse(resp_text)
        self.assertIsNotNone(res_json.get('ref'))
        self.shared.set(res_json.get('ref'), "store01_ref")

        # Make sure result is as expected
        self.assertJsonTextEqual(resp_text, result)

    def test11_store_get(self):
        '''Test GET for RStore get'''
        result = self.get_data("store01_result.txt")
        key = self.shared.get("store01_ref")
        resp = self.get("/rstore/%s" % key)
        resp_text = resp.get_data()
        self.assertJsonTextEqual(resp_text, result)

    def test12_store_put(self):
        '''Test GET for RStore put'''
        data = self.get_data("store01_update.json")
        key = self.shared.get("store01_ref")
        resp = self.put("/rstore/%s" % key, data)

        resp_text = resp.get_data()
        res_json = READER.parse(resp_text)
        self.assertEqual(res_json.get('ref'), key)
        self.assertEqual(res_json.get('city'), "Milan")
        self.assertEqual(res_json.get('name'), "Milan Store")

        self.shared.set(resp_text, "store01_resp")

    def test20_person_query(self):
        '''Person query'''
        resp = self.get("/rperson/")
        resp_text = resp.get_data()

        # Create expected dictionary
        expected = {}
        expected[self.shared.get('person01_key')] = READER.parse(self.shared.get('person01_resp'))
        expected[self.shared.get('person02_key')] = READER.parse(self.shared.get('person02_resp'))

        # Convert resulting list to a key based dictionary
        res_json = READER.parse(resp_text)
        result = {}
        rcount = 0
        for entry in res_json:
            rcount += 1
            result[entry.get('key')] = entry

        self.assertDictEqual(result, expected)

        # Make sure result count is the same as db
        self.assertEqual(RPerson.query().count(), rcount)


    def test21_store_query(self):
        '''Store query'''
        resp = self.get("/rstore/")
        resp_text = resp.get_data()

        # Create expected dictionary
        expected = {}
        expected[self.shared.get('store01_ref')] = READER.parse(self.shared.get('store01_resp'))

        # Convert resulting list to a key based dictionary
        res_json = READER.parse(resp_text)
        result = {}
        for entry in res_json:
            result[entry.get('ref')] = entry

        self.assertDictEqual(result, expected)

    def test30_person_delete(self):
        '''Delete query'''
        resp = self.delete("/rperson/%s" % self.shared.get('person01_key'))
        self.assertEqual(resp.get_data(), "")

        # Make sure that only one person left
        self.assertEqual(RPerson.query().count(), 1)

    def test35_store_delete(self):
        '''Store delete should raise error'''
        resp = self.delete("/rstore/%s" % self.shared.get('store01_key'), check_response=False)
        # HTTP code of 405 is Method Not Allowed
        self.assertEqual(resp.status_code, 405)


class AppRouteTest(BaseRouteTest):
    '''
    Make sure that RESTRouteGenerator will work on a flask app
    '''
    datastore_mode = "normal"

    @classmethod
    def setUpClass(cls):
        testlib.SharedTestData.unload()
        cls.shared = testlib.SharedTestData()
        cls.maxDiff = None
        cls.app = Flask(cls.__name__)
        rgen = RESTRouteGenerator(cls.app)
        rgen.setup_model_view(RPerson)
        rgen.setup_model_view(RStore, action_verbs=('POST', 'QUERY', 'GET', 'PUT'))


class BlueprintRouteTest(BaseRouteTest):
    '''
    Make sure that RESTRouteGenerator will work on a blueprint
    '''
    datastore_mode = "normal"

    @classmethod
    def setUpClass(cls):
        testlib.SharedTestData.unload()
        cls.shared = testlib.SharedTestData()
        cls.maxDiff = None
        cls.app = Flask(cls.__name__)
        cls.base_url = "/dd/"
        bprint = Blueprint("BP_%s" % cls.__name__, "blueprint_%s" % cls.__name__)
        rgen = RESTRouteGenerator(bprint)
        rgen.setup_model_view(RPerson)
        rgen.setup_model_view(RStore, action_verbs=('POST', 'QUERY', 'GET', 'PUT'))

        cls.app.register_blueprint(bprint, url_prefix=cls.base_url)


if __name__ == '__main__':
    # TestRunner is needed here as it will setup the datastore
    testlib.TestRunner.run(AppRouteTest, verbosity=2, failfast=True)
    testlib.TestRunner.run(BlueprintRouteTest, verbosity=2, failfast=True)
