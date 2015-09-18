cd /home/ec2-user/isiscb

# This is necessary for virtualenvwrapper (mkvirtualenv, workon) to work.
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

workon isiscb

# Supervisor manages gunicorn. See awsdeploy/supervisor.conf.
supervisorctl -c /etc/supervisor/conf.d/supervisor.conf start isiscb
