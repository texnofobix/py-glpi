# glpi-sdk-python

[![Build Status](https://travis-ci.org/truly-systems/glpi-sdk-python.svg?branch=master)](https://travis-ci.org/truly-systems/glpi-sdk-python)
![PyPi version](https://img.shields.io/pypi/v/glpi.svg)


GLPI SDK written in Python.

## Description

This SDK is written in Python to help developers integrate their apps, APIS and scripts in GLPI infrastructure. This SDK abstract
the [GLPI Rest API](https://github.com/glpi-project/glpi/blob/9.1/bugfixes/apirest.md).

To usage it, you should have username, password and API-Token from your GLPI server.

To create an API token: Setup > General > API :
* `Enable Rest API` : `Yes`

See also:
* [GLPI Rest API](https://github.com/glpi-project/glpi/blob/9.1/bugfixes/apirest.md#glpi-rest-api--documentation)


## Install

Just install from:

* PyPi:

  ```bash
  pip install glpi
  ```

* repository (development):

  ```bash
  pip install -e git+https://github.com/truly-systems/glpi-sdk-python.git@master#egg=glpi
  ```

* requirements.txt (development)

    ```shell
    pip install -r requirements-dev.txt
    ```

## Usage

You should enable the GLPI API and generate an App Token.

Please, export these environments variables with yours config:

  ```bash
  export username = "GLPI_USER"
  export password = "GLPI_USER"
  export url = 'http://glpi.example.com/apirest.php'
  export glpi_app_token = "GLPI_API_TOKEN"
  ```

Then import it in your script and create a `glpi` API connection:

  ```python
  import os
  from glpi import GLPI

  url = os.getenv("GLPI_API_URL") or None
  user = os.getenv("GLPI_USERNAME") or None
  password = os.getenv("GLPI_PASSWORD") or None
  token = os.getenv("GLPI_APP_TOKEN") or None

  glpi = GLPI(url, token, (user, password))
  glpi.kill() #Destroy a session identified by a session token
  ```

To usage the SDK, you just set the DBTM item that you want and get information from GLPI.

The Item value must be valid, otherwise you will get the following error.

```shell
[
    "ERROR_RESOURCE_NOT_FOUND_NOR_COMMONDBTM",
    "resource not found or not an instance of CommonDBTM; view documentation in your browser at http://<GLPI_URL>/apirest.php/#ERROR_RESOURCE_NOT_FOUND_NOR_COMMONDBTM"
]
```

### Profile information

  ```python
  print "Getting all the profiles associated to logged user: "
  print json.dumps(glpi.get('getMyProfiles'),
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```

### Get active profile

  ```python
  print "Getting the current active profile: "
  print json.dumps(glpi.get('getActiveProfile'),
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```

### Change active profile

  ```python
  print "Changing active profile to the profiles_id one: "

  ticket_dict = glpi.post(item_name='changeActiveProfile', item_id=1, is_recursive=True)
  #is_recursive: (default false) Also display sub entities of the active entity
  ```

### Get my entities

  ```python
  print "Getting all the possible entities of the current logged user: "
  print json.dumps(glpi.get('getMyEntities'),
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```

### Get active entities

  ```python
  print "Getting active entities of current logged user: "
  print json.dumps(glpi.get('getActiveEntities'),
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```

### Change active entities

  ```python
  print "Changing active entity to the entities_id one: "

  ticket_dict = glpi.post(item_name='changeActiveEntities', item_id=1)
  ```

### Get full session

  ```python
  print "Getting the current php $_SESSION: "
  print json.dumps(glpi.get('getFullSession'),
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```
  

### Get all Tickets

  ```python
  print "Getting all Tickets: "
  print json.dumps(glpi.get_all('ticket'),
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```

### Get ticket by ID

  ```python
  print "Getting Ticket with ID 1: "
  print json.dumps(glpi.get('ticket', 1),
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```

### Get sub items

  ```python
  print "Getting a collection of rows of the sub_itemtype for the identified item: "
  print json.dumps(glpi.get('ticket', 1, 'log'),
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```

### Location

  ```python
  print "Getting 'Locations': "
  print json.dumps(glpi.get('location'),
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```


### Create an Ticket

  ```python

  ticket_payload = {
    'name': 'New ticket from SDK',
    'content': '>>>> Content of ticket created by SDK API <<<'
  }

  ticket_dict = glpi.create(item_name='ticket', item_data=ticket_payload)
  if isinstance(ticket_dict, dict):
    print "The create ticket request was sent. See results: "

  print json.dumps(ticket_dict,
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```

### Update an Ticket

  ```python

  ticket_payload = {
    'name': 'New name of ticket from SDK',
    'content': '>>>> New content of ticket created by SDK API <<<'
    'id': 1 #Id value generated in creation of ticket
  }

  ticket_dict = glpi.update(item_name='ticket', data=ticket_payload)
  if isinstance(ticket_dict, dict):
    print "The update ticket request was sent. See results: "

  print json.dumps(ticket_dict,
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```

### Delete an Ticket

  ```python

  ticket_dict = glpi.delete(item_name='ticket', item_id=1, force_purge=true) 
  #force_purge (default false): boolean, if the itemtype have a dustbin, you can force purge (delete finally)
  if isinstance(ticket_dict, dict):
    print "The delete ticket request was sent. See results: "

  print json.dumps(ticket_dict,
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```

### List searchOptions

  ```python
  print "Getting a list of search options for the item type provided: "
  print json.dumps(glpi.search_options('ticket'),
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```

### Search with GLPI search engine

GLPI has a powerfull search engine builtin, which is exposed via the API.
See the documentation at your GLPI instance via `apirest.php#search-items`.

The usage sample using `curl` is:

> query 'name' and return the ID

```bash
curl -X GET 'http://path/to/apirest.php/search/Knowbaseitem?
    criteria\[0\]\[field\]\=6
    &criteria\[0\]\[searchtype\]=contains
    &criteria\[0\]\[value\]=sites-multimidia
    &criteria\[0\]\[link\]\=AND
    &criteria\[1\]\[field\]\=2
    &criteria\[1\]\[searchtype\]\=contains
    &criteria\[1\]\[value\]\=
    &criteria\[1\]\[link\]\=AND'
```

You can use it as follows:

```python
  print "Search 'Computers': "
  criteria = { "criteria": [
                {
                  # "link": "AND", # this is optional for the first criterion
                  "searchtype": None, # default to "contains"
                  "field": "name",
                  "value": "TEST"
                },
                {
                  "link": "AND",
                  #"searchtype": "bb", # default to "contains"
                  "field": "otherserial",
                  "value": "xxx"
                }
             ]}
  print json.dumps(glpi.search_engine('computer', criteria),
                    indent=4,
                    separators=(',', ': '),
                    sort_keys=True)
  ```

**Usage:**

* `field` parameter:
  * You can use field names instead of their integer IDs (see output from
    `/listSearchOptions`)
    * These names are taken from their `uid`, but the item type is stripped.
    * If you need a special field from a plugin, just find out the corresponding
      `uid` and strip the item type.
    * Example: `{"1": {"uid": "Computer.name"}}` gets `{"name": 1}` for type
      *Computer*
  * If you provide an integer or a number as string, it won't be touched
    before use.
  * If you provide an unmappable field name, an exception is raised.
* `searchtype` is entirely optional, accepts garbage and `None`.
* `link` is only enforced on criterions that are not the first.
* `value` is entirely optional like `searchtype`.

**Limitations:**

* You cannot use other search parameters other than `criteria` right now.
* You cannot use the `metacriteria` parameter, which makes linked searches
  unavailable.

### Full example

> TODO: create an full example with various Items available in GLPI Rest API.

## CONTRIBUTING

See [CONTRIBUTING.md](CONTRIBUTING.md)
