cd /home/ec2-user/isiscb

# This is necessary for virtualenvwrapper (mkvirtualenv, workon) to work.
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

workon isiscb

# Shut down gunicorn gracefully.
supervisorctl -c /etc/supervisor/conf.d/supervisor.conf stop isiscb
supervisorctl -c /etc/supervisor/conf.d/supervisor.conf shutdown
