# api.ox.ac.uk — core services

This is Alex's prototype for delivering an API framework for the University of Oxford. It's **experimental**.

It aims to provide a common authentication platform and authorization framework, to deliver user-focussed APIs.

Authentication-wise, it will support:

* Kerberos (negotiate auth)
* OAuth2
* Basic auth (for those that can't do Kerberos)

It's written in Python and uses `asyncio` and `aiohttp` for concurrency.

