cd /home/ec2-user/isiscb

# This is necessary for virtualenvwrapper (mkvirtualenv, workon) to work.
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

workon isiscb
touch server_start 
chmod 666 server_start 

# Supervisor manages gunicorn. See awsdeploy/supervisor.conf.
supervisorctl -c /etc/supervisor/conf.d/supervisor.conf start isiscb
