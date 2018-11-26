
==================
    Questions
==================


Certificates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

I'm getting an `SSLError` when accessing stats.

The default certificate setup on your system should work for most
cases. If you have additional certificates installed or have them
stored in a different location exporting the following environment
variable might help you::

    REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt
