# coding: utf-8
"""
Sentry stats such as commented, resolved issues

Configuration example::

    [sentry]
    type = sentry
    url = http://sentry.usersys.redhat.com/api/0/
    token = ...

You need to generate authentication token
at http://sentry.usersys.redhat.com/api/.
The only scope you need to check is `org:read`.
"""

from __future__ import absolute_import, unicode_literals

import json
import urllib2

from did.base import Config, ReportError
from did.stats import Stats, StatsGroup
from did.utils import log, pretty, split


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sentry Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

token = ""
url = "http://sentry.usersys.redhat.com/api/0/organizations/baseos/activity/"
headers = {'Authorization': 'Bearer {0}'.format(token)}
request = urllib2.Request(url, None, headers)
try: response = urllib2.urlopen(request)
except urllib2.URLError as e:
    print e.reason

data = json.load(response)

user = "makopec@redhat.com"
since = "2017-08-14"
until = "2017-08-18"


def assigned():
    status = ""
    count = 0
    for activity in data:
        if activity['dateCreated'] > since and activity['dateCreated'] < until and \
            activity['user']['username'] == user and activity["type"] == 'set_resolved':
            status += "\t{0} - {1}\n".format(activity['issue']['shortId'], activity['issue']['title'])
            count += 1
    print "Assigned to myself: {0}".format(count)
    print status

def resolved():
    status = ""
    count = 0
    for activity in data:
        if activity['dateCreated'] > since and activity['dateCreated'] < until and \
            activity['user']['username'] == user and activity["type"] == 'assigned' and \
            activity['data']['assigneeEmail'] == user:
            status += "\t{0} - {1}\n".format(activity['issue']['shortId'], activity['issue']['title'])
            count += 1
    print "Set to resolved: {0}".format(count)
    print status

def commented():
    status = ""
    count = 0
    for activity in data:
        if activity['dateCreated'] > since and activity['dateCreated'] < until and \
            activity['user']['username'] == user and activity["type"] == 'note':
            status += "\t{0} - {1}\n".format(activity['issue']['shortId'], activity['issue']['title'])
            count += 1
    print "Commented on: {0}".format(count)
    print status


assigned()
resolved()
commented()
