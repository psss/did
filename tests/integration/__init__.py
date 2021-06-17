import xmlrpc.client

import nitrate
from bugzilla._backendxmlrpc import _BugzillaXMLRPCTransport
from requests import sessions
from requre import cassette
from requre.cassette import StorageKeysInspectSimple
from requre.helpers.guess_object import Guess
from requre.helpers.requests_response import RequestResponseHandling

# decorate functions what communicates with nitrate
nitrate.xmlrpc_driver.GSSAPITransport.single_request = Guess.decorator_plain()(
    nitrate.xmlrpc_driver.GSSAPITransport.single_request)
nitrate.xmlrpc_driver.GSSAPITransport.single_request_with_cookies = Guess.decorator_plain()(
    nitrate.xmlrpc_driver.GSSAPITransport.single_request_with_cookies)

# decorate functions that communicate with bugzilla (xmlrpc)
_BugzillaXMLRPCTransport.single_request = Guess.decorator_plain()(
    _BugzillaXMLRPCTransport.single_request)
sessions.Session.send = RequestResponseHandling.decorator(
    item_list=[1])(
        sessions.Session.send)

# use storage simple strategy to avoid use full stack info for keys
cassette.StorageKeysInspectDefault = StorageKeysInspectSimple
