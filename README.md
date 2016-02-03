# IsisCB [![Build Status](https://travis-ci.org/upconsulting/IsisCB.svg?branch=develop)](https://travis-ci.org/upconsulting/IsisCB)

Current version: 0.12.2

## License

This software is licensed under the terms of the The MIT License. For more
information, see ``LICENSE.md`` in this repository.

## Deployment

IsisCB is designed to run in the Amazon Web Services environment. The file
``appspec.yml`` defines the process for deploying to an EC2 instance via
CodeDeploy..

Since it's a Django app, it can be deployed as a WSGI application. We use
[Gunicorn](http://gunicorn.org/) running behind a [nginx](https://www.nginx.com)
proxy server. For details on configuring nginx to work with Gunicorn,
see [this documentation](http://docs.gunicorn.org/en/latest/deploy.html).

Here is one procedure for deploying IsisCB from scratch:

1. [Install Python2.7.x](#1-install-python27x)
2. [Install system packages](#2-install-system-packages)
3. [Install pip](#3-install-pip)
4. [Download and unpack IsisCB](#4-download-and-unpack-isiscb)
5. [Install Python dependencies in requirements.txt](#5-install-python-dependencies-in-requirementstxt)
6. [Configure settings.py](#6-configure-settingspy)
7. [Install and configure ``nginx``](#7-install-and-configure-nginx)
8. [Configure ``gunicorn``](#8-configure-gunicorn)
9. [Configure ``supervisor``](#9-configure-supervisor)
10. [Initialize database](#10-initialize-database)
11. [Launch!](#11-launch)

### 1. Install Python2.7.x

IsisCB is developed for Python 2.7. Chances are, this version of Python is
already installed on your system. If not, you can download it from
[python.org](https://www.python.org/).

### 2. Install system packages

In order for all dependencies to install correctly, you'll need to make sure
that you have the following packages installed:

* unixodbc-dev
* openssl
* postgresql_psycopg2

You can use the package manager if your choice. E.g. via
[Homebrew](http://brew.sh/):

```shell
$ brew install unixodbc-dev openssl postgresql_psycopg2
```

### 3. Install pip

As of Python 2.7.9, pip ships along with your Python installation. To verify
that pip is installed, try:

```shell
$ pip -V
```

An easy way to install pip is via the get-pip.py script:

```shell
$ curl https://bootstrap.pypa.io/get-pip.py -o - | python
```

For more information, see [https://pip.pypa.io/en/latest/installing.html](https://pip.pypa.io/en/latest/installing.html).

### 4. Download and unpack IsisCB

You can find the latest version of IsisCB in our
[GitHub repository](https://github.com/upconsulting/IsisCB). Download
the entire repository (e.g. as a
[ZIP file](https://github.com/upconsulting/IsisCB/archive/master.zip)), and
unpack it wherever you keep your apps.

### 5. Install Python dependencies in requirements.txt

The file ``requirements.txt`` describes all of the Python dependencies for
IsisCB. Install them all at once using:

```shell
$ cd /path/to/unzipped/isiscb
$ pip install -r requirements.txt
```

**Note**: you may want to use an isolated environment of some kind, e.g.
[virtualenv](https://virtualenv.pypa.io/en/latest/). We use
[virtualenvwrapper](https://virtualenvwrapper.readthedocs.org/en/latest/). So
you would first create the virtualenv, and install the dependencies therein:

```shell
$ mkvirtualenv isiscb
$ workon isiscb
$ cd /path/to/unzipped/isiscb
$ pip install -r requirements.txt
```

### 6. Configure settings.py

In the IsisCB GitHub repository you'll find several settings.py files, e.g.
``local_settings.py``, ``development_settings.py``, etc. You can either modify
one of those files to suit your needs, or create a new one.

In particular, you'll need to configure your database backend, and settings
dealing with static files.

Our database configuration for our development server looks like this:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'isiscb',
        'USER': '{username}',
        'PASSWORD': '{password}',
        'HOST': 'isiscb-develop-db.fjd93j2.us-west-2.rds.amazonaws.com',
        'PORT': '5432',
    }
}
```

Note that Django will expect to find a database called ``isiscb`` already
created.

We use the following configuration to host static and media files on Amazon
S3. [This tutorial](https://www.caktusgroup.com/blog/2014/11/10/Using-Amazon-S3-to-store-your-Django-sites-static-and-media-files/)
provides an excellent introduction to using S3 with Django, although some of the
details of the configuration are outdated. If you use a configuration like this,
you'll also need to update the ``bucket_name`` fields in the storage classes
defined in ``custom_storages.py``.

```python
AWS_STORAGE_BUCKET_NAME = 'isiscb-develop-staticfiles'
AWS_MEDIA_BUCKET_NAME = 'isiscb-develop-media'
AWS_ACCESS_KEY_ID = '{access key}'
AWS_SECRET_ACCESS_KEY = '{secret key}'
AWS_S3_CUSTOM_DOMAIN = 's3.amazonaws.com'
AWS_S3_SECURE_URLS = False

STATICFILES_LOCATION = '%s/static' % AWS_STORAGE_BUCKET_NAME
STATICFILES_STORAGE = 'custom_storages.StaticStorage'
STATIC_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, STATICFILES_LOCATION)

MEDIAFILES_LOCATION = '%s/media' % AWS_MEDIA_BUCKET_NAME
MEDIA_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, MEDIAFILES_LOCATION)
DEFAULT_FILE_STORAGE = 'custom_storages.MediaStorage'

AWS_HEADERS = {
    'Expires': 'Thu, 31 Dec 2099 20:00:00 GMT',
    'Cache-Control': 'max-age=94608000',
}
```

Complete documentation for settings.py can be found
[here](https://docs.djangoproject.com/en/1.8/topics/settings/).

To select your configuration, set the ``DJANGO_SETTINGS_MODULE`` environment
variable. For example:

```shell
$ DJANGO_SETTINGS_MODULE="isiscb.development_settings"
$ export DJANGO_SETTINGS_MODULE
```

### 7. Install and configure ``nginx``

You can install nginx using your favorite package manager. For example:

```shell
$ brew install nginx
```

See [this documentation](http://docs.gunicorn.org/en/latest/deploy.html) for
details about configuring nginx to work with Gunicorn. We use the following
configuration. Note that you'll have to change several of the paths (those
starting with ``/home/ec2-user``), and note the location where nginx expects to
find the ``gunicorn.sock`` file.

```
worker_processes 1;

pid /tmp/nginx.pid;
error_log /tmp/nginx.error.log;

events {
    worker_connections 1024;
    accept_mutex off;
}

http {
    server_names_hash_bucket_size 128;
    include mime.types;
    default_type application/octet-stream;
    access_log /tmp/nginx.access.log combined;
    sendfile on;

    upstream app_server {
        server unix:/tmp/gunicorn.sock fail_timeout=0;
    }

    server {
        listen 80 default_server;
        return 444;
    }

    server {
        listen 80;
        client_max_body_size 4G;

        # set the correct host(s) for your site
        server_name isiscb-develop.aplacecalledup.com;

        keepalive_timeout 5;

        # path for static files
        #root /home/ec2-user/isiscb/static;

        location / {
            try_files $uri @proxy_to_app;
        }

        location @proxy_to_app {
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $http_host;
            proxy_redirect off;

            proxy_pass   http://app_server;
        }

        error_page 500 502 503 504 /500.html;
        location = /500.html {
            root /home/ec2-user/isiscb/static;
        }
    }
}
```

You can start nginx with:

```shell
$ sudo nginx
```

To stop nginx, use:

```shell
$ sudo nginx -s stop
```

### 8. Configure ``gunicorn``

We use a script called ``gunicorn_start`` to serve IsisCB via Gunicorn, shown
below. You'll need to modify some lines based on the specifics of your
deployment (e.g. file paths, location of socket file).

```shell
#!/bin/sh

cd /home/ec2-user/isiscb

# This is necessary for virtualenvwrapper (mkvirtualenv, workon) to work.
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

NAME="isiscb"
DJANGODIR=/home/ec2-user/isiscb/isiscb  # Directory that contains manage.py.
SOCKFILE=/tmp/gunicorn.sock             # nginx connects here.
NUM_WORKERS=3
DJANGO_WSGI_MODULE=isiscb.wsgi

echo "Starting $NAME as `whoami`"

cd $DJANGODIR
workon isiscb

RUNDIR=$(dirname $SOCKFILE)
test -d $RUNDIR || mkdir -p $RUNDIR

exec gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $NUM_WORKERS \
  --bind=unix:$SOCKFILE \
  --log-level=debug \
  --log-file=-
```

### 9. Configure ``supervisor``

We use [supervisor](http://supervisord.org/) to manage Gunicorn and other
processes. Our ``supervisor.conf`` file can be found in ``awsdeploy``.

In addition to the standard supervisor configuration blocks, you'll need
to configure a program block for IsisCB based on your environment. Ours looks
like this:

```
[program:isiscb]
; isiscb is a Python WSGI application served by Gunicorn on a UNIX socket.
command = /home/ec2-user/isiscb/awsdeploy/bin/gunicorn_start
stdout_logfile = /home/ec2-user/isiscb/logs/gunicorn_supervisor.log
redirect_stderr = true
environment=LANG=en_US.UTF-8,LC_ALL=en_US.UTF-8
```

We store our configuration file at ```/etc/supervisor/conf.d/supervisor.conf```
upon deployment.

### 10. Initialize database

Before running IsisCB for the first time, you'll need to initialize the
database. In the folder containing ```manage.py``, run the following commands:

```shell
$ python manage.py makemigrations
$ python manage.py migrate
$ python manage.py createsuperuser
```

If you run into trouble here, there is likely something wrong with your database
configuration.

### 11. Launch!

If everything goes according to plan, you should be able to start IsisCB using
supervisor. Our start-up procedure looks like this:

Start supervisor:

```shell
$ supervisord -c /etc/supervisor/conf.d/supervisor.conf
$ supervisorctl -c /etc/supervisor/conf.d/supervisor.conf reread
$ supervisorctl -c /etc/supervisor/conf.d/supervisor.conf update
```

Update static files and perform any new migrations:

```shell
$ python manage.py collectstatic --noinput
$ python manage.py migrate
```

Start the IsisCB app:

```shell
$ supervisorctl -c /etc/supervisor/conf.d/supervisor.conf start isiscb
```

You can monitor the status of the application using:

```shell
$ supervisorctl -c /etc/supervisor/conf.d/supervisor.conf status
isiscb                           RUNNING   pid 7227, uptime 1:35:00
```
