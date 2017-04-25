
from flask import request, jsonify, json, Response, Blueprint
from flask.views import MethodView
from werkzeug.exceptions import BadRequest, NotFound, MethodNotAllowed, InternalServerError

from models import NdbModelError, NdbModelMismatchError, InvalidKeyError
from views import NdbViewMixIn, NdbViewError, ViewValueError, KeyMisMatchViewError

from core import ConfigurationStore, scream_print

with ConfigurationStore() as c:
    LOGGER = c.logger

# Translate of action verb to http verb
SUPPORTED_VERBS = {
    'POST': 'POST',
    'QUERY': 'GET',
    'GET': 'GET',
    'PUT': 'PUT',
    'DELETE': 'DELETE'
}

# ==============================================================================
# Define Exceptions
#
class MissingInputJsonRequestError(BadRequest):
    def __init__(self, description=None, response=None):
        if description is None:
            description = "No valid json from from the request"
        super(MissingInputJsonRequestError, self).__init__(description, response)

# ==============================================================================
# Define RestAction
#
class FlaskUtils(object):

    @classmethod
    def _check_none_result(cls, data, not_found_message):
        if data is None:
            if not_found_message is None:
                raise BadRequest("None passed to FlaskUtil.response and `not_found_message` not set.")
            else:
                raise NotFound(not_found_message)

    @classmethod
    def _json_generator(cls, list_or_generator, **kwargs):
        '''Iterate a list or generator that yield a ndb.Model or dictionary, returns JSON array'''
        first_row = True
        yield "["

        for entry in list_or_generator:
            json_text = json.dumps(entry, **kwargs)
            if first_row:
                yield json_text
                first_row = False
            else:
                yield ", %s" % json_text

        yield "]"

    @classmethod
    def validate_json_request(cls, req):
        '''
        Raise appropriate error when input JSON does not exists or mal formed.
        Used normally in a POST request.
        '''
        try:
            in_dict = req.get_json()
        except BadRequest:
            LOGGER.error("FlaskUtils.validate_json_request got BadRequest", exc_info=True)
            raise MissingInputJsonRequestError()

        if in_dict is None:
            LOGGER.error("FlaskUtils.validate_json_request received NUL JSON")
            raise MissingInputJsonRequestError()
        return in_dict

    @classmethod
    def response(cls, data, not_found_message=None):
        '''Return a JSON response'''
        cls._check_none_result(data, not_found_message)
        return jsonify(data)

    @classmethod
    def response_query(cls, query, **kwargs):
        '''Return a JSON response of a list'''
        return Response(cls._json_generator(query, **kwargs), mimetype="application/json")


class BaseMethodView(MethodView):
    '''
    BaseMethodView that binds a ndb.Model with NdbViewMixIn to itself allowing
    auto configuaration of routes using RESTRouteGenerator
    '''
    _ndb_view = None

    def get(self, urlsafe_key=None):
        '''
        Handle GET verb for both .query (without urlsafe param) or .get (with urlsafe param)

        Exception: NotFound, MethodNotAllowed, BadRequest, InternalServerError
        '''
        if urlsafe_key is None:
            try:
                result = self._ndb_view.view_query()
            except StandardError as ex:
                LOGGER.error("%s QUERY InternalServerError: %s [%s]", self.__class__.__name__, ex, ex.__class__.__name__, exc_info=True)
                raise InternalServerError("Unexpected error: %s" % ex)
            LOGGER.debug("%s QUERY: %s", self.__class__.__name__, result)
            return FlaskUtils.response_query(result)
        else:
            try:
                result = self._ndb_view.view_get(urlsafe_key)
            except InvalidKeyError as ex:
                LOGGER.error("%s GET BadRequest: %s [%s]", self.__class__.__name__, ex, ex.__class__.__name__)
                raise BadRequest(ex)
            except StandardError as ex:
                LOGGER.error("%s GET InternalServerError: %s [%s]", self.__class__.__name__, ex, ex.__class__.__name__, exc_info=True)
                raise InternalServerError("Unexpected error: %s" % ex)
            LOGGER.debug("%s GET with key: %s", self.__class__.__name__, urlsafe_key)
            return FlaskUtils.response(result, not_found_message="Key '%s' not found." % urlsafe_key)

    def post(self):
        '''
        Handle POST verb.

        Exception: MissingInputJsonRequestError, BadRequest, InternalServerError
        '''

        in_json = FlaskUtils.validate_json_request(request)
        LOGGER.debug("%s POST with json: %s", self.__class__.__name__, in_json)
        try:
            result = self._ndb_view.view_create(in_json)
        except (NdbViewError, InvalidKeyError, NdbModelMismatchError) as ex:
            LOGGER.error("%s POST BadRequest: %s [%s]", self.__class__.__name__, ex, ex.__class__.__name__)
            raise BadRequest(ex)
        except StandardError as ex:
            LOGGER.error("%s POST InternalServerError: %s [%s]", self.__class__.__name__, ex, ex.__class__.__name__, exc_info=True)
            raise InternalServerError("Unexpected error: %s" % ex)

        return FlaskUtils.response(result)

    def put(self, urlsafe_key):
        '''
        Handle PUT verb.

        Exception: NotFound, MissingInputJsonRequestError, BadRequest, InternalServerError
        '''
        in_json = FlaskUtils.validate_json_request(request)
        LOGGER.debug("%s PUT [k=%s] with json : %s", self.__class__.__name__, urlsafe_key, in_json)
        try:
            result = self._ndb_view.view_update(in_json, in_key=urlsafe_key)
        except (ViewValueError, KeyMisMatchViewError) as ex:
            LOGGER.error("%s PUT BadRequest: %s [%s]", self.__class__.__name__, ex, ex.__class__.__name__)
            raise BadRequest(ex)
        except StandardError as ex:
            LOGGER.error("%s PUT InternalServerError: %s [%s]", self.__class__.__name__, ex, ex.__class__.__name__, exc_info=True)
            raise InternalServerError(ex)

        return FlaskUtils.response(result, not_found_message="Key '%s' not found." % urlsafe_key)

    def delete(self, urlsafe_key):
        '''
        Handle DELETE verb

        Exception: BadRequest
        '''
        LOGGER.debug("%s DELETE [k=%s]", self.__class__.__name__, urlsafe_key)
        try:
            self._ndb_view.view_delete(urlsafe_key)
        except InvalidKeyError as ex:
            LOGGER.error("%s DELETE BadRequest: %s [%s]", self.__class__.__name__, ex, ex.__class__.__name__)
            raise BadRequest(ex)
        except StandardError as ex:
            LOGGER.error("%s DELETE InternalServerError: %s [%s]", self.__class__.__name__, ex, ex.__class__.__name__, exc_info=True)
            raise InternalServerError(ex)
        return Response(status=200)


class RESTRouteGenerator(object):
    '''
    Return a simple blueprint wiring view to CRUD operations
    '''
    def __init__(self, flask_app):
        self._app = flask_app
        self._accepted_action_verbs = set(SUPPORTED_VERBS.keys())

    def _set_url_from_verb(self, action_verbs, url, route_view, var_name):
        pass

    def setup_method_view(self, method_view, name, key_param=None, action_verbs=None):
        '''
        Create route for the method_view passed.

        `method_view`:  A BaseMethodView based class (class itself and not an instance of the class)
        `base_url`:     Base url to be used for setting up the routes
        `key_param`:    The string that will be used on the flask URL for the key
        `action_verbs`: List of verbs to setup
        '''

        # Check method_view passed
        if not issubclass(method_view, BaseMethodView):
            raise TypeError("model_view object passed is not an instance of BaseMethodView")

        # Check action verbs
        if action_verbs is None:
            averbs = self._accepted_action_verbs.copy()
        else:
            averbs = set(action_verbs)
            if not averbs.issubset(self._accepted_action_verbs):
                raise TypeError("Action verbs passed '%s' contains unsupported verbs" % str(action_verbs))

        # Setup routes
        base_url = "/%s/" % name.lower()
        LOGGER.debug("Setting '%s' method_view for url '%s' with verbs '%s'", method_view.__name__, base_url, str(averbs))

        view_func = method_view.as_view(name)

        if "QUERY" in averbs:
            LOGGER.debug("Adding QUERY rule.")
            self._app.add_url_rule(base_url, view_func=view_func, methods=['GET',])
            averbs.remove("QUERY")

        if "POST" in averbs:
            LOGGER.debug("Adding POST rule.")
            self._app.add_url_rule(base_url, view_func=view_func, methods=['POST',])
            averbs.remove("POST")

        if averbs:
            url = "%s%s" % (base_url, key_param)
            LOGGER.debug("Adding '%s' rules for url of '%s'", str(averbs), url)
            self._app.add_url_rule(url, view_func=view_func, methods=averbs)

    def setup_model_view(self, model_view, name=None, decorators=None, action_verbs=None):
        '''
        Create a MethodView from the ModelView passed and create the needed routes.

        `model_view`:   A ndb.Model with NdbViewMixIn
        `name`:         Object name to use for the class and the path
                        default to the name of the `view`
        `key_param`:    The string that will be used on the flask URL for the key
        `decorators`:   The decorator to be used on the MethodView
        `action_verbs`: a list of one of: QUERY, GET, POST, PUT, PATCH, DELETE
        '''
        if not issubclass(model_view, NdbViewMixIn):
            raise TypeError("model_view object passed is not an instance of NdbViewMixIn")

        if name is None:
            name = model_view.__name__


        # Create a MethodView class on the fly
        LOGGER.debug("Creating a ViewMethod from '%s' with name '%s'", model_view.__name__, name)
        class_args = {
            '_ndb_view': model_view
        }
        if decorators:
            class_args['decorators'] = decorators
        class_name = "MethodView_%s" % name
        GeneratedMethodView = type(class_name, (BaseMethodView,), class_args) # pylint: disable=C0103
        key_param = "<string:urlsafe_key>"

        self.setup_method_view(GeneratedMethodView, name, key_param=key_param, action_verbs=action_verbs)
