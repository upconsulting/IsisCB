cd /home/ec2-user/isiscb

export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

mkvirtualenv isiscb
workon isiscb

pip install -r requirements.txt

chmod u+x awsdeploy/bin/gunicorn_start
touch logs/gunicorn_supervisor.log

supervisorctl reread
supervisorctl update
