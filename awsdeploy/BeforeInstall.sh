export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

mkvirtualenv isiscb
workon isiscb

pip install -r /home/ec2-user/isiscb/requirements.txt

chmod u+x /home/ec2-user/isiscb/awsdeploy/bin/gunicorn_start
touch /home/ec2-user/isiscb/logs/gunicorn_supervisor.log

supervisorctl reread
supervisorctl update
