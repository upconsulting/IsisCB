cd /home/ec2-user/isiscb

# This is necessary for virtualenvwrapper (mkvirtualenv, workon) to work.
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

# Select the development configuration. See development_settings.py.
DJANGO_SETTINGS_MODULE="isiscb.development_settings"
export DJANGO_SETTINGS_MODULE

mkvirtualenv isiscb
workon isiscb

# Install (new) Python dependencies.
pip install -r requirements.txt

# Supervisor manages Gunicorn, and perhaps other services down the road.
#  supervisor.conf is updated (overwritten) on each deploy, so this loads
#  the new configuration.
supervisord -c /etc/supervisor/conf.d/supervisor.conf
supervisorctl -c /etc/supervisor/conf.d/supervisor.conf reread
supervisorctl -c /etc/supervisor/conf.d/supervisor.conf update

# Static files are hosted on S3. This will push any new or updated static files
#  to the appropriate bucket (see development_settings.py).
cd isiscb
python manage.py collectstatic --noinput
python manage.py migrate
