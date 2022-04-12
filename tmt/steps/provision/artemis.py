import datetime
import time
from typing import Any, Dict, Optional, cast

import click
import requests

import tmt
from tmt.utils import ProvisionError, updatable_message

# TODO: find out how to get this one into RPM builds.
try:
    from typing_extensions import TypedDict

except ImportError:
    TypedDict = None


# List of Artemis API versions supported and understood by this plugin.
# Since API gains support for new features over time, it is important to
# know when particular feature became available, and avoid using it with
# older APIs.
SUPPORTED_API_VERSIONS = (
    '0.0.28', '0.0.32'
    )

# The default Artemis API version - the most recent supported versions
# should be perfectly fine.
DEFAULT_API_VERSION = SUPPORTED_API_VERSIONS[-1]

# Type annotation for "data" package describing a guest instance. Passed
# between load() and save() calls.
if TypedDict is None:
    GuestDataType = Dict[str, Any]

else:
    GuestDataType = TypedDict(
        'DataType',
        {
            # API
            'api-url': str,
            'api-version': str,

            # Guest request properties
            'arch': str,
            'image': str,
            'hardware': Any,
            'pool': Optional[str],
            'priority-group': str,
            'keyname': str,
            'user-data': Dict[str, str],

            # Provided by Artemis response
            'guestname': Optional[str],
            'guest': Optional[str],
            'user': str,

            # Timeouts and deadlines
            'provision-timeout': int,
            'provision-tick': int,
            'api-timeout': int,
            'api-retries': int,
            'api-retry-backoff-factor': int
            }
        )

DEFAULT_USER = 'root'
DEFAULT_ARCH = 'x86_64'
DEFAULT_PRIORITY_GROUP = 'default-priority'
DEFAULT_KEYNAME = 'default'
DEFAULT_PROVISION_TIMEOUT = 600
DEFAULT_PROVISION_TICK = 60
DEFAULT_API_TIMEOUT = 10
DEFAULT_API_RETRIES = 10
# Should lead to delays of 0.5, 1, 2, 4, 8, 16, 32, 64, 128, 256 seconds
DEFAULT_RETRY_BACKOFF_FACTOR = 1

DEFAULT_GUEST_DATA = cast(
    GuestDataType, {
        'api-version': DEFAULT_API_VERSION,
        'arch': DEFAULT_ARCH,
        'priority-group': DEFAULT_PRIORITY_GROUP,
        'keyname': DEFAULT_KEYNAME,
        'user-data': {},
        'user': DEFAULT_USER,
        'provision-timeout': DEFAULT_PROVISION_TIMEOUT,
        'provision-tick': DEFAULT_PROVISION_TICK,
        'api-timeout': DEFAULT_API_TIMEOUT,
        'api-retries': DEFAULT_API_RETRIES,
        'api-retry-backoff-factor': DEFAULT_RETRY_BACKOFF_FACTOR
        }
    )

GUEST_STATE_COLOR_DEFAULT = 'green'

GUEST_STATE_COLORS = {
    'routing': 'yellow',
    'provisioning': 'magenta',
    'promised': 'blue',
    'preparing': 'cyan',
    'cancelled': 'red',
    'error': 'red'
}


# Type annotation for Artemis API `GET /guests/$guestname` response.
# Partial, not all fields necessary since plugin ignores most of them.
if TypedDict is None:
    GuestInspectType = Dict[str, Any]

else:
    GuestInspectType = TypedDict(
        'GuestInspectType', {
            'state': str,
            'address': Optional[str]
            }
        )


class TimeoutHTTPAdapter(requests.adapters.HTTPAdapter):
    """
    Spice up request's session with custom timeout.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.timeout = kwargs.pop('timeout', DEFAULT_API_TIMEOUT)

        super().__init__(*args, **kwargs)

    def send(
            self,
            request: requests.PreparedRequest,
            **kwargs: Any) -> requests.Response:    # type: ignore
        kwargs.setdefault('timeout', self.timeout)

        return super().send(request, **kwargs)


class ArtemisAPI:
    def install_http_retries(
            self,
            timeout: int,
            retries: int,
            retry_backoff_factor: int
            ) -> None:
        """
        Install custom "retry strategy" and timeout to our HTTP session.

        Strategy and timeout work together, "consuming" the timeout as
        specified by the strategy.
        """

        retry_strategy = requests.packages.urllib3.util.retry.Retry(
            total=retries,
            status_forcelist=[
                429,  # Too Many Requests
                500,  # Internal Server Error
                502,  # Bad Gateway
                503,  # Service Unavailable
                504   # Gateway Timeout
                ],
            method_whitelist=[
                'HEAD', 'GET', 'POST', 'DELETE', 'PUT'
                ],
            backoff_factor=retry_backoff_factor
            )

        timeout_adapter = TimeoutHTTPAdapter(
            timeout=timeout,
            max_retries=retry_strategy
            )

        self.http_session.mount('https://', timeout_adapter)
        self.http_session.mount('http://', timeout_adapter)

    def __init__(self, guest: 'GuestArtemis') -> None:
        self._guest = guest

        self.http_session = requests.Session()

        self.install_http_retries(
            timeout=guest.api_timeout,
            retries=guest.api_retries,
            retry_backoff_factor=guest.api_retry_backoff_factor
            )

    def query(
            self,
            path: str,
            method: str = 'get',
            request_kwargs: Optional[Dict[str, Any]] = None
            ) -> requests.Response:
        """
        Base helper for Artemis API queries.

        Trivial dispatcher per method, returning retrieved response.

        :param path: API path to contact.
        :param method: HTTP method to use.
        :param request_kwargs: optional request options, as supported by
            :py:mod:`requests` library.
        """

        request_kwargs = request_kwargs or {}

        url = f'{self._guest.api_url}{path}'

        if method == 'get':
            return self.http_session.get(url, **request_kwargs)

        if method == 'post':
            return self.http_session.post(url, **request_kwargs)

        if method == 'delete':
            return self.http_session.delete(url, **request_kwargs)

        if method == 'put':
            return self.http_session.put(url, **request_kwargs)

        raise tmt.utils.GeneralError(
            f'Unsupported Artemis API method.\n{method}')

    def create(
            self,
            path: str,
            data: Dict[str, Any],
            request_kwargs: Optional[Dict[str, Any]] = None
            ) -> requests.Response:
        """
        Create - or request creation of - a resource.

        :param path: API path to contact.
        :param data: optional key/value data to send with the request.
        :param request_kwargs: optional request options, as supported by
            :py:mod:`requests` library.
        """

        request_kwargs = request_kwargs or {}
        request_kwargs['json'] = data

        return self.query(path, method='post', request_kwargs=request_kwargs)

    def inspect(
            self,
            path: str,
            params: Optional[Dict[str, Any]] = None,
            request_kwargs: Optional[Dict[str, Any]] = None
            ) -> requests.Response:
        """
        Inspect a resource.

        :param path: API path to contact.
        :param params: optional key/value query parameters.
        :param request_kwargs: optional request options, as supported by
            :py:mod:`requests` library.
        """

        request_kwargs = request_kwargs or {}

        if params:
            request_kwargs['params'] = params

        return self.query(path, request_kwargs=request_kwargs)

    def delete(
            self,
            path: str,
            request_kwargs: Optional[Dict[str, Any]] = None
            ) -> requests.Response:
        """
        Delete - or request removal of - a resource.

        :param path: API path to contact.
        :param request_kwargs: optional request options, as supported by
            :py:mod:`requests` library.
        """

        return self.query(path, method='delete', request_kwargs=request_kwargs)


class ProvisionArtemis(tmt.steps.provision.ProvisionPlugin):
    """
    Provision guest using Artemis backend

    Minimal configuration could look like this:

        provision:
            how: artemis
            image: Fedora
            api-url: https://your-artemis.com/

    Note that the actual value of "image" depends on what images - or
    "composes" as Artemis calls them - supports and can deliver.

    Note that "api-url" can be also given via ARTEMIS_API_URL
    environment variable.

    Full configuration example:

        provision:
            how: artemis

            # Artemis API
            api-url: https://your-artemis.com/
            api-version: 0.0.32

            # Mandatory environment properties
            image: Fedora

            # Optional environment properties
            arch: aarch64
            pool: optional-pool-name

            # Provisioning process control (optional)
            priority-group: custom-priority-group
            keyname: custom-SSH-key-name

            # Labels to be attached to guest request (optional)
            user-data:
                foo: bar

            # Timeouts and deadlines (optional)
            provision-timeout: 3600
            provision-tick: 10
            api-timeout: 600
            api-retries: 5
            api-retry-backoff-factor: 1
    """

    # Guest instance
    _guest = None

    # Supported methods
    _methods = [
        tmt.steps.Method(name='artemis', doc=__doc__, order=50),
        ]

    _keys = [
        'api-url',
        'api-version',
        'arch',
        'image',
        'hardware',
        'pool',
        'priority-group',
        'keyname',
        'user-data',
        'provision-timeout',
        'provision-tick',
        'api-timeout',
        'api-retries',
        'api-retry-backoff-factor']

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for Artemis """
        return [
            click.option(
                '--api-url', metavar='URL',
                help="Artemis API URL.",
                envvar='ARTEMIS_API_URL'
                ),
            click.option(
                '--api-version', metavar='x.y.z',
                help="Artemis API version to use.",
                type=click.Choice(SUPPORTED_API_VERSIONS),
                envvar='ARTEMIS_API_VERSION'
                ),
            click.option(
                '--arch', metavar='ARCH',
                help='Architecture to provision.'
                ),
            click.option(
                '--image', metavar='COMPOSE',
                help='Image (or "compose" in Artemis terminology) '
                     'to provision.'
                ),
            click.option(
                '--pool', metavar='NAME',
                help='Pool to enforce.'
                ),
            click.option(
                '--priority-group', metavar='NAME',
                help='Provisioning priority group.'
                ),
            click.option(
                '--keyname', metavar='NAME',
                help='SSH key name.'
                ),
            click.option(
                '--user-data', metavar='KEY=VALUE',
                help='Optional data to attach to guest.',
                multiple=True,
                default=[]
                ),
            click.option(
                '--provision-timeout', metavar='SECONDS',
                help=f'How long to wait for provisioning to complete, '
                     f'{DEFAULT_PROVISION_TIMEOUT} seconds by default.'
                ),
            click.option(
                '--provision-tick', metavar='SECONDS',
                help=f'How often check Artemis API for provisioning status, '
                     f'{DEFAULT_PROVISION_TICK} seconds by default.',
                ),
            click.option(
                '--api-timeout', metavar='SECONDS',
                help=f'How long to wait for API operations to complete, '
                     f'{DEFAULT_API_TIMEOUT} seconds by default.',
                ),
            click.option(
                '--api-retries', metavar='COUNT',
                help=f'How many attempts to use when talking to API, '
                     f'{DEFAULT_API_RETRIES} by default.',
                ),
            click.option(
                '--api-retry-backoff-factor', metavar='COUNT',
                help=f'A factor for exponential API retry backoff, '
                     f'{DEFAULT_RETRY_BACKOFF_FACTOR} by default.',
                ),
            ] + super().options(how)

    def default(self, option, default=None):
        """ Return default data for given option """

        return DEFAULT_GUEST_DATA.get(option, default)

    def wake(self, keys=None, data=None):
        """ Wake up the plugin, process data, apply options """

        super().wake(keys=keys, data=data)

        if data:
            self._guest = GuestArtemis(data, name=self.name, parent=self.step)

    def go(self):
        """ Provision the guest """
        super().go()

        api_version = self.get('api-version')

        if api_version not in SUPPORTED_API_VERSIONS:
            raise ProvisionError(f"API version '{api_version}' not supported.")

        try:
            user_data = {
                key.strip(): value.strip()
                for key, value in (
                    pair.split('=', 1)
                    for pair in self.get('user-data')
                    )
                }

        except ValueError as exc:
            raise ProvisionError('Cannot parse user-data.')

        data: GuestDataType = {
            'api-url': self.get('api-url'),
            'api-version': api_version,
            'arch': self.get('arch'),
            'image': self.get('image'),
            'hardware': self.get('hardware'),
            'pool': self.get('pool'),
            'priority-group': self.get('priority-group'),
            'keyname': self.get('keyname'),
            'user-data': user_data,
            'guestname': None,
            'guest': None,
            'user': DEFAULT_USER,
            'provision-timeout': self.get('provision-timeout'),
            'provision-tick': self.get('provision-tick'),
            'api-timeout': self.get('api-timeout'),
            'api-retries': self.get('api-retries'),
            'api-retry-backoff-factor': self.get('api-retry-backoff-factor')
            }

        self._guest = GuestArtemis(data, name=self.name, parent=self.step)
        self._guest.start()

    def guest(self):
        """ Return the provisioned guest """
        return self._guest


class GuestArtemis(tmt.Guest):
    """
    Artemis guest instance

    The following keys are expected in the 'data' dictionary:
    """

    _api: Optional[ArtemisAPI] = None

    @property
    def api(self) -> ArtemisAPI:
        if self._api is None:
            self._api = ArtemisAPI(self)

        return self._api

    def load(self, data: GuestDataType):
        super().load(data)

        self.api_url = data['api-url']
        self.api_version = data['api-version']
        self.arch = data['arch']
        self.image = data['image']
        self.hardware = data['hardware']
        self.pool = data['pool']
        self.priority_group = data['priority-group']
        self.keyname = data['keyname']
        self.user_data = data['user-data']
        self.guestname = data['guestname']
        self.guest = data['guest']
        self.user = data['user']
        self.provision_timeout = data['provision-timeout']
        self.provision_tick = data['provision-tick']
        self.api_timeout = data['api-timeout']
        self.api_retries = data['api-retries']
        self.api_retry_backoff_factor = data['api-retry-backoff-factor']

    def save(self):
        data = cast(GuestDataType, super().save())

        data['api-url'] = self.api_url
        data['api-version'] = self.api_version
        data['arch'] = self.arch
        data['image'] = self.image
        data['hardware'] = self.hardware
        data['pool'] = self.pool
        data['priority-group'] = self.priority_group
        data['keyname'] = self.keyname
        data['user-data'] = self.user_data
        data['guestname'] = self.guestname
        data['guest'] = self.guest
        data['user'] = self.user
        data['provision-timeout'] = self.provision_timeout
        data['provision-tick'] = self.provision_tick
        data['api-timeout'] = self.api_timeout
        data['api-retries'] = self.api_retries
        data['api-retry-backoff-factor'] = self.api_retry_backoff_factor

        return data

    def _create(self) -> None:
        environment: Dict[str, Any] = {
            'hw': {
                'arch': self.arch
                },
            'os': {
                'compose': self.image
                }
            }

        data: Dict[str, Any] = {
            'environment': environment,
            'keyname': self.keyname,
            'priority_group': self.priority_group,
            'user_data': self.user_data
            }

        if self.pool:
            environment['pool'] = self.pool

        if self.hardware is not None:
            assert isinstance(self.hardware, dict)

            environment['hw']['constraints'] = self.hardware

        # TODO: snapshots
        # TODO: spot instance
        # TODO: post-install script
        # TODO: log types

        response = self.api.create('/guests/', data)

        if response.status_code == 201:
            self.info('guest', 'has been requested', 'green')

        else:
            raise ProvisionError(
                f"Failed to create, "
                f"unhandled API response '{response.status_code}'.")

        self.guestname = response.json()['guestname']
        self.info('guestname', self.guestname, 'green')

        deadline = datetime.datetime.utcnow(
            ) + datetime.timedelta(seconds=self.provision_timeout)

        with updatable_message(
                'state', indent_level=self._level()) as progress_message:
            while deadline > datetime.datetime.utcnow():
                response = self.api.inspect(f'/guests/{self.guestname}')

                if response.status_code != 200:
                    raise ProvisionError(
                        f"Failed to create, "
                        f"unhandled API response '{response.status_code}'.")

                current = cast(GuestInspectType, response.json())
                state = current['state']
                state_color = GUEST_STATE_COLORS.get(
                    state, GUEST_STATE_COLOR_DEFAULT)

                progress_message.update(state, color=state_color)

                if state == 'error':
                    raise ProvisionError(
                        f'Failed to create, provisioning failed.')

                if state == 'ready':
                    break

                time.sleep(self.provision_tick)

            else:
                raise ProvisionError(
                    f'Failed to provision in the given amount '
                    f'of time (--provision-timeout={self.provision_timeout}).')

        self.guest = current['address']
        self.info('address', self.guest, 'green')

    def start(self):
        """
        Start the guest

        Get a new guest instance running. This should include preparing
        any configuration necessary to get it started. Called after
        load() is completed so all guest data should be available.
        """

        if self.guestname is None or self.guest is None:
            self._create()

    def remove(self):
        """ Remove the guest """

        if self.guestname is None:
            return

        response = self.api.delete(f'/guests/{self.guestname}')

        if response.status_code == 404:
            self.info('guest', 'no longer exists', 'red')

        elif response.status_code == 409:
            self.info('guest', 'has existing snapshots', 'red')

        elif response.ok:
            self.info('guest', 'has been removed', 'green')

        else:
            self.info(
                'guest',
                f"Failed to remove, "
                f"unhandled API response '{response.status_code}'.")
