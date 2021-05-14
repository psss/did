import nitrate
from requre import cassette
from requre.cassette import StorageKeysInspectSimple
from requre.helpers.guess_object import Guess

# decorate functions what communicates with nitrate
nitrate.xmlrpc_driver.GSSAPITransport.single_request = Guess.decorator_plain()(
    nitrate.xmlrpc_driver.GSSAPITransport.single_request)
nitrate.xmlrpc_driver.GSSAPITransport.single_request_with_cookies = Guess.decorator_plain()(
    nitrate.xmlrpc_driver.GSSAPITransport.single_request_with_cookies)

# use storage simple strategy to avoid use full stack info for keys
cassette.StorageKeysInspectDefault = StorageKeysInspectSimple
