# IsisCB 

[![Build Status](https://travis-ci.org/upconsulting/IsisCB.svg?branch=develop)](https://travis-ci.org/upconsulting/IsisCB) <img alt="GitHub release" src="https://img.shields.io/github/release/upconsulting/isisCB">

## License

This software is licensed under the terms of the The MIT License. For more
information, see ``LICENSE.md`` in this repository.

## Deployment

There is a Docker Compose setup available to run the Explore system for development. To start the Docker containers run the following command from the root directory of this project.

`docker-compose -f docker-compose-explore.yml up`

If you have existing database, you will first have to import the existing data into the Docker container PostgreSQL database before running the Explore system's container.

# Contributors

The [Explore system](https://isiscb.org/) is being developed by [A Place Called Up Consulting](http://aplacecalledup.com/) for Stephen P. Weldon, University of Oklahoma. The following people are currently or have been contributing to the development:

- Julia Damerow
- Erick B. Peirson
- Taylor Quinn
- Paul Vieth
