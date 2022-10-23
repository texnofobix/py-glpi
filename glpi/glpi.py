# Copyright 2017 Predict & Truly Systems All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# GLPI API Rest documentation:
# https://github.com/glpi-project/glpi/blob/9.1/bugfixes/apirest.md

from __future__ import print_function
from future.utils import viewitems
import re
import os
import sys
import json as json_import
import logging
import requests
from requests.structures import CaseInsensitiveDict
from .version import __version__

if sys.version_info[0] > 2:
    from html.parser import HTMLParser
else:
    from HTMLParser import HTMLParser


logger = logging.getLogger(__name__)


def load_from_vcap_services(service_name):
    vcap_services = os.getenv("VCAP_SERVICES")
    if vcap_services is not None:
        services = json_import.loads(vcap_services)
        if service_name in services:
            return services[service_name][0]["credentials"]
    else:
        return None


def _remove_null_values(dictionary):
    if isinstance(dictionary, dict):
        return dict([(k, v) for k, v in dictionary.items() if v is not None])
    return dictionary


def _cleanup_param_value(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return value


def _cleanup_param_values(dictionary):
    if isinstance(dictionary, dict):
        return dict(
            [(k, _cleanup_param_value(v)) for k, v in dictionary.items()])
    return dictionary


def _glpi_html_parser(content):
    """
    Try to retrieve data tokens from HTML content.
    It's useful to debug GLPI rest when it's not returning JSON responses. I.E:
    when MYSQL server is down, API Rest answer html errors.
    """
    class GlpiHTMLParser(HTMLParser):
        def __init__(self, content):
            HTMLParser.__init__(self)
            self.count = 0
            self.data = []
            self.feed(content)

        def get_count(self):
            return self.count

        def get_data(self):
            return self.data

        def get_data_clear(self):
            """ Get data tokens without comments '/' """
            new_data = []
            for r in self.get_data():
                if r.startswith('/'):
                    continue
                new_data.append(r)
            return new_data

        def handle_data(self, data):
            """ Get data tokens in HTML feed """
            d = data.strip()
            if d:
                self.count += 1
                self.data.append(d)

    html_parser = GlpiHTMLParser(content)
    return html_parser.get_data_clear()


class GlpiException(Exception):
    pass


class GlpiInvalidArgument(GlpiException):
    pass


class GlpiService(object):
    """ Polymorphic class of GLPI REST API Service. """
    __version__ = __version__

    def __init__(self, url_apirest, token_app, uri=None,
                 username=None, password=None, token_auth=None,
                 use_vcap_services=False, vcap_services_name=None):
        """
        [TODO] Loads credentials from the VCAP_SERVICES environment variable if
        available, preferring credentials explicitly set in the request.
        If VCAP_SERVICES is not found (or use_vcap_services is set to False),
        username and password credentials must be specified.

        You can choose in setup initial authentication using username and
        password, or setup with Authorization HTTP token. If token_auth is set,
        username and password credentials must be ignored.
        """
        self.__version__ = __version__
        self.url = url_apirest
        self.app_token = token_app
        self.uri = uri

        self.username = username
        self.password = password
        self.token_auth = token_auth

        self.session = None

        if token_auth is not None:
            if username is not None or password is not None:
                raise GlpiInvalidArgument(
                    'Cannot set token_auth and username and password together')
            self.set_token_auth(token_auth)
        else:
            self.set_username_and_password(username, password)

        if use_vcap_services and not self.username and not self.token_auth:
            self.vcap_service_credentials = load_from_vcap_services(
                vcap_services_name)
            if self.vcap_service_credentials is not None and isinstance(
                    self.vcap_service_credentials, dict):
                self.url = self.vcap_service_credentials['url']
                if 'username' in self.vcap_service_credentials:
                    self.username = self.vcap_service_credentials['username']
                if 'password' in self.vcap_service_credentials:
                    self.password = self.vcap_service_credentials['password']
                if 'token_auth' in self.vcap_service_credentials:
                    self.token_auth =\
                        self.vcap_service_credentials['token_auth']
                if 'app_token' in self.vcap_service_credentials:
                    self.app_token = self.vcap_service_credentials['app_token']

        if self.app_token is None:
            raise GlpiException(
                'You must specify GLPI API-Token(app_token) to make API calls')

        if (self.username is None or self.password is None)\
                and self.token_auth is None:
            raise GlpiException(
                'You must specify your username and password, or token_auth'
                'service credentials ')

    def set_username_and_password(self, username=None, password=None):
        if username == 'YOUR SERVICE USERNAME':
            username = None
        if password == 'YOUR SERVICE PASSWORD':
            password = None

        self.username = username
        self.password = password

    def set_token_auth(self, token_auth):
        if token_auth == 'YOUR AUTH TOKEN':
            token_auth = None

        self.token_auth = token_auth

    def set_uri(self, uri):
        self.uri = uri

    def get_version(self):
        return self.__version__

    """
    Session Token
    """
    def set_session_token(self):
        """ Set up new session ID """

        # URL should be like: http://glpi.example.com/apirest.php
        full_url = self.url + '/initSession'
        auth = None

        headers = {"App-Token": self.app_token,
                   "Content-Type": "application/json"}

        if type(self.token_auth) is not tuple: # self.token_auth is not None:
            headers["Authorization"] = "user_token "+self.token_auth
        else:
            auth = self.token_auth

        try:
            if r.status_code == 200:
                self.session = r.json()['session_token']
                return True
            else:
                err = _glpi_html_parser(r.content)
                raise GlpiException("Failed to init session: %s" % err)
        except Exception:
            err = _glpi_html_parser(r.content)
            raise GlpiException("ERROR init session: %s" % err)

        return False

    def finish_session_token(self):
        """ Destroy a session identified by a session token """

        if self.session is not None:
            # URL should be like: http://glpi.example.com/apirest.php
            full_url = self.url + '/killSession'
            auth = None

            headers = {
                    "App-Token": self.app_token,
                    "Content-Type": "application/json",
                    "Session-Token": self.session
                }

            if self.token_auth is not None:
                auth = self.token_auth
            else:
                auth = (self.username, self.password)

            r = requests.request('GET', full_url, auth=auth, headers=headers)

            try:
                if r.status_code == 200:
                    return True
                else:
                    err = _glpi_html_parser(r.content)
                    raise GlpiException("Failed to finish session: %s" % err)
            except Exception:
                err = _glpi_html_parser(r.content)
                raise GlpiException("Eroor to finish session: %s" % err)

        return False

    def get_session_token(self):
        """ Returns current session ID """

        if self.session is not None:
            return self.session
        else:
            try:
                self.set_session_token()
                return self.session
            except GlpiException:
                raise

            else:
                return 'Unable to get Session Token'

    def update_session_token(self, session_id):
        """ Update session ID """

        if session_id:
            self.session = session_id

        return self.session

    """ Request """
    def request(self, method, url, accept_json=False, headers={},
                params=None, json=None, data=None, files=None, **kwargs):
        """
        Make a request to GLPI Rest API.
        Return response object.
        (http://docs.python-requests.org/en/master/api/#requests.Response)
        """

        full_url = '%s/%s' % (self.url, url.strip('/'))
        input_headers = _remove_null_values(headers) if headers else {}

        headers = CaseInsensitiveDict(
             {'user-agent': 'glpi-sdk-python-' + __version__})

        if accept_json:
            headers['accept'] = 'application/json'

        try:
            if self.session is None:
                self.set_session_token()
            headers.update({'Session-Token': self.session})
        except GlpiException as e:
            raise GlpiException("Unable to get Session token: {}".format(e))

        if self.app_token is not None:
            headers.update({'App-Token': self.app_token})

        headers.update(input_headers)

        # Remove keys with None values
        params = _remove_null_values(params)
        params = _cleanup_param_values(params)
        json = _remove_null_values(json)
        data = _remove_null_values(data)
        files = _remove_null_values(files)

        try:
            response = requests.request(method=method, url=full_url,
                                        headers=headers, params=params,
                                        data=data, **kwargs)
        except Exception:
            logger.error("ERROR requesting uri(%s) payload(%s)" % (url, data))
            raise

        return response

    def get_payload(self, data_json):
        """ Construct the payload for REST API from JSON data. """

        data_str = ""
        null_str = "<DEFAULT_NULL>"
        for k in data_json:
            if data_str != "":
                data_str = "%s," % data_str

            if data_json[k] == null_str:
                data_str = '%s "%s": null' % (data_str, k)
            elif isinstance(data_json[k], str):
                data_str = '%s "%s": "%s"' % (data_str, k, data_json[k])
            else:
                data_str = '%s "%s": %s' % (data_str, k, str(data_json[k]))

        return data_str

    """ Generic Items methods """
    # [C]REATE - Create an Item
    def create(self, data_json=None):
        """ Create an object Item. """

        if (data_json is None):
            return "{ 'error_message' : 'Object not found.'}"

        payload = '{"input": { %s }}' % (self.get_payload(data_json))

        response = self.request('POST', self.uri,
                                data=payload, accept_json=True)

        return response.json()

    # [R]EAD - Retrieve Item data
    def get_all(self):
        """ Return all content of Item in JSON format. """

        res = self.request('GET', self.uri)
        return res.json()

    def get(self, item_id):
        """ Return the JSON item with ID item_id. """

        if isinstance(item_id, (int, str)):
            uri = '%s/%s' % (self.uri, str(item_id))
            response = self.request('GET', uri)
            return response.json()
        else:
            return {'error_message': 'Unale to get %s ID [%s]' % (self.uri,
                                                                  item_id)}

    def get_path(self, path=''):
        """ Return the JSON from path """
        response = self.request('GET', path)
        return response.json()

    def search_options(self, item_name):
        """
        List search options for an Item to be used in
        search_engine/search_query.
        """
        new_uri = "%s/%s" % (self.uri, item_name)
        response = self.request('GET', new_uri, accept_json=True)

        return response.json()

    def search_engine(self, search_query):
        """
        Search an item by URI.
        Use GLPI search engine passing parameter by URI.
        #TODO could pass search criteria in payload, like others items
        operations.
        """
        new_uri = "%s/%s" % (self.uri, search_query)
        response = self.request('GET', new_uri, accept_json=True)

        return response.json()

    def post(self, item_id, is_recursive=False, change=None):
        """ Change an object Item(Profile or entity) """

        if not isinstance(item_id, int):
            return {"message_error": "Please define item_id to be deleted."}

        if change == "changeActiveEntities":
            if is_recursive:
                payload = '{"entities_id": %d,"is_recursive":true}' % (item_id)
            else:
                payload = '{"entities_id": %d }' % (item_id)

        if change == "changeActiveProfile":
            payload = '{"profiles_id": %d}' % (item_id)

        response = self.request('POST', self.uri, data=payload)
        if response.text == "":
            return {"status": True}
        return response.json()

    # [U]PDATE an Item
    def update(self, data):
        """ Update an object Item. """

        payload = '{"input": { %s }}' % (self.get_payload(data))
        new_url = "%s/%d" % (self.uri, data['id'])

        response = self.request('PUT', new_url, data=payload)

        return response.json()

    # [D]ELETE an Item
    def delete(self, item_id, force_purge=False):
        """ Delete an object Item. """

        if not isinstance(item_id, int):
            return {"message_error": "Please define item_id to be deleted."}

        if force_purge:
            payload = '{"input":{ "id": %d },"force_purge": true}' % (item_id)
        else:
            payload = '{"input":{ "id": %d}}' % (item_id)

        response = self.request('DELETE', self.uri, data=payload)
        return response.json()


class GLPI(object):
    """
    Generic implementation of GLPI Items can manage all
    Itens in one GLPI server connection.
    We can use this class to save implementation of "new classes" and
    can reuse API sessions.
    To support new items you should create the dict key/value in item_map.
    """
    __version__ = __version__

    def __init__(self, url, app_token, auth_token,
                 item_map=None):
        """ Construct generic object """

        self.url = url
        self.app_token = app_token
        self.auth_token = auth_token

        self.item_uri = None
        self.item_map = {
            "ticket": "/Ticket",
            "knowbase": "/knowbaseitem",
            "listSearchOptions": "/listSearchOptions",
            "search": "/search",
            "user": "user",
            "getFullSession": "getFullSession",
            "getActiveProfile": "getActiveProfile",
            "getMyProfiles": "getMyProfiles",
            "location": "location",
            "getMyEntities": "getMyEntities",
            "getActiveEntities": "getActiveEntities",
            "changeActiveEntities": "changeActiveEntities",
            "changeActiveProfile": "changeActiveProfile"
        }
        self.api_rest = None
        self.api_session = None

        if item_map is not None:
            self.set_item_map(item_map)

    def help_item(self):
        """ Help item values """
        return {"available_items": self.item_map}

    def set_item(self, item_name):
        """ Define an item to object """
        try:
            self.item_uri = self.item_map[item_name]
        except KeyError as e:
            raise Exception('Key [{}] not found. {}'.format(item_name, e))
        except Exception as e:
            raise e

    def set_item_map(self, item_map={}):
        """ Set an custom item_map. """
        self.item_map = item_map

    def set_api_uri(self):
        """
        Update URI in Service API object.
        We should do this every new Item requested.
        """
        self.api_rest.set_uri(self.item_uri)

    def update_uri(self, item_name):
        """ Avoid duplicate calls in every 'Item operators' """
        if (item_name not in self.item_map):
            if item_name.startswith('/'):
                item_name_real = item_name.split('/')[1]
                self.item_map.update({item_name_real: item_name})
                item_name = item_name_real
            else:
                _item_path = '/' + item_name
                self.item_map.update({item_name: _item_path})

        self.set_item(item_name)
        self.set_api_uri()

    def init_api(self):
        """ Initialize the API Rest connection """

        self.api_rest = GlpiService(self.url, self.app_token,
                                    token_auth=self.auth_token)

        try:
            self.api_session = self.api_rest.get_session_token()
        except GlpiException:
            raise

        if self.api_session is not None:
            return {"session_token": self.api_session}
        else:
            return {"message_error": "Unable to InitSession in GLPI Server."}

    def kill(self):
        try:
            if self.api_has_session():
                self.api_rest.finish_session_token()
                self.api_rest = None
                self.api_session = None
        except GlpiException as e:
            return {'{}'.format(e)}

    def api_has_session(self):
        """
        Check if API has session cfg or if it is enalbed
        """
        if self.api_session is None:
            return False

        return True

    # [C]REATE - Create an Item
    def create(self, item_name, item_data):
        """ Create an Resource Item """
        try:
            if not self.api_has_session():
                self.init_api()

            self.update_uri(item_name)
            return self.api_rest.create(item_data)

        except GlpiException as e:
            return {'{}'.format(e)}

    # [R]EAD - Retrieve Item data
    def get_all(self, item_name):
        """ Get all resources from item_name """
        try:
            if not self.api_has_session():
                self.init_api()

            self.update_uri(item_name)
            return self.api_rest.get_all()

        except GlpiException as e:
            return {'{}'.format(e)}

    def get(self, item_name, item_id=None, sub_item=None):
        """ Get item_name and/with resource by ID """
        try:
            if not self.api_has_session():
                self.init_api()

            self.update_uri(item_name)

            if sub_item is not None and item_id is not None:
                return self.api_rest.get("%d/%s" % (item_id, sub_item))

            if item_id is None:
                return self.api_rest.get_path(item_name)

            return self.api_rest.get(item_id)

        except GlpiException as e:
            return {'{}'.format(e)}

    def post(self, item_name, item_id, is_recursive=False):
        """ POST item_name (Profile or entity) """
        try:
            if not self.api_has_session():
                self.init_api()

            self.update_uri(item_name)
            return self.api_rest.post(item_id, is_recursive=is_recursive,
                                      change=item_name)

        except GlpiException as e:
            return {'{}'.format(e)}

    def search_options(self, item_name):
        """ List GLPI APIRest Search Options """
        try:
            if not self.api_has_session():
                self.init_api()

            self.update_uri('listSearchOptions')
            return self.api_rest.search_options(item_name)

        except GlpiException as e:
            return {'{}'.format(e)}

    def search_criteria(self, data, criteria):
        """ #TODO Search in data some criteria """
        result = []
        for d in data:
            find = False
            for c in criteria:
                if c['value'].lower() in d[c['field']].lower():
                    find = True
            if find:
                result.append(d)
        return result

    def search_metacriteria(self, metacriteria):
        """ TODO: Search in metacriteria in source Item """
        return {"message_info": "Not implemented yet"}

    def search(self, item_name, criteria):
        """ #SHOULD BE IMPROVED
        Return an Item with that matchs with criteria
        criteria: [
            {
                "field": "name",
                "value": "search value"
            }
        ]
        """
        if 'criteria' in criteria:
            data = self.get_all(item_name)
            return self.search_criteria(data, criteria['criteria'])
        elif 'metacriteria' in criteria:
            return self.search_metacriteria(criteria['metacriteria'])
        else:
            return {"message_error": "Unable to find a valid criteria."}

    def search_engine(self, item_name, criteria):
        """
        Call GLPI's search engine syntax.

        INPUT query in JSON format (/apirest.php#search-items):
        metacriteria: [
            {
                "link": 'AND'
                "searchtype": "contais",
                "field": "name",
                "value": "search value"
            }
        ]

        RETURNS:
            GLPIs APIRest JSON formated with result of search in key 'data'.
        """

        # Receive the possible field ids for type item_name
        # -> to avoid wrong lookups, use uid of fields, but strip item type:
        #    example: {"1": {"uid": "Computer.name"}} gets {"name": 1}
        field_map = {}
        opts = self.search_options(item_name)
        for field_id, field_opts in viewitems(opts):
            if field_id.isdigit() and 'uid' in field_opts:
                # support case-insensitive strip from item_name!
                field_name = re.sub('^'+item_name+'.', '', field_opts['uid'],
                                    flags=re.IGNORECASE)
                field_map[field_name] = int(field_id)

        uri_query = "%s?" % item_name

        for idx, c in enumerate(criteria['criteria']):
            # build field argument
            if idx == 0:
                uri = ""
            else:
                uri = "&"
            if 'field' in c and c['field'] is not None:
                field_name = ""
                # if int given, use it directly
                if isinstance(c['field'], int) or c['field'].isdigit():
                    field_name = int(c['field'])
                # if name given, try to map to an int
                elif c['field'] in field_map:
                    field_name = field_map[c['field']]
                else:
                    raise GlpiInvalidArgument(
                        'Cannot map field name "' + c['field'] + '" to ' +
                        'a field id for '+str(idx+1)+'. criterion '+str(c))
                uri = uri + "criteria[%d][field]=%d" % (idx, field_name)
            else:
                raise GlpiInvalidArgument(
                    'Missing "field" parameter for ' + str(idx+1) +
                    'the criteria: ' + str(c))

            # build value argument
            if 'value' not in c or c['value'] is None:
                uri = uri + "&criteria[%d][value]=" % (idx)
            else:
                uri = uri + "&criteria[%d][value]=%s" % (idx, c['value'])

            # build searchtype argument
            # -> optional! defaults to "contains" on the server if empty
            if 'searchtype' in c and c['searchtype'] is not None:
                uri = (uri + "&criteria[%d][searchtype]=%s".format(idx,
                       c['searchtype']))
            else:
                uri = uri + "&criteria[%d][searchtype]=" % (idx)

            # link is optional for 1st criterion according to docs...
            # -> error if not present but more than one criterion
            if 'link' not in c and idx > 0:
                raise GlpiInvalidArgument(
                    'Missing link type for '+str(idx+1)+'. criterion '+str(c))
            elif 'link' in c:
                uri = uri + "&criteria[%d][link]=%s" % (idx, c['link'])

            # add this criterion to the query
            uri_query = uri_query + uri

        try:
            if not self.api_has_session():
                self.init_api()

            self.update_uri('search')
            # TODO: is this call correct? shouldn't this be search_engine()?
            return self.api_rest.search_options(uri_query)

        except GlpiException as e:
            return {'{}'.format(e)}

    # [U]PDATE an Item
    def update(self, item_name, data):
        """ Update an Resource Item. Should have all the Item payload """
        try:
            if not self.api_has_session():
                self.init_api()

            self.update_uri(item_name)
            return self.api_rest.update(data)

        except GlpiException as e:
            return {'{}'.format(e)}

    # [D]ELETE an Item
    def delete(self, item_name, item_id, force_purge=False):
        """ Delete an Resource Item. Should have all the Item payload """
        try:
            if not self.api_has_session():
                self.init_api()

            self.update_uri(item_name)
            return self.api_rest.delete(item_id, force_purge=force_purge)

        except GlpiException as e:
            return {'{}'.format(e)}
