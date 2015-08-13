cd /home/ec2-user/isiscb

export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

mkvirtualenv isiscb
workon isiscb

pip install -r requirements.txt

chmod +x /home/ec2-user/isiscb/awsdeploy/bin/gunicorn_start
touch logs/gunicorn_supervisor.log

supervisord -c /etc/supervisor/conf.d/supervisor.conf
Error: The directory named as part of the path /var/log/supervisord/supervisord.log does not exi
supervisorctl -c /etc/supervisor/conf.d/supervisor.conf reread
supervisorctl -c /etc/supervisor/conf.d/supervisor.conf update

cd isiscb
python manage.py collectstatic
