# IsisCB 

[![Build Status](https://travis-ci.org/upconsulting/IsisCB.svg?branch=develop)](https://travis-ci.org/upconsulting/IsisCB) <img alt="GitHub release" src="https://img.shields.io/github/release/upconsulting/isisCB">

## License

This software is licensed under the terms of the The MIT License. For more
information, see ``LICENSE.md`` in this repository.

## Deployment

IsisCB Explore can be run as a WSGI application, e.g. using Gunicorn behind
NginX, or in Apache using mod_wsgi.

The main application should be run from ``isiscb.wsgi``.

Worker processes should be run from ``isiscb.celery``.


